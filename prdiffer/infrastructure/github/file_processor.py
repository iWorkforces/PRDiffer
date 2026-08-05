"""File processing service for GitHub repositories."""

import inspect
import time
import anyio
import asyncer
from typing import Any, Sequence, cast
from github.File import File
from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest as PyGithubPullRequest
from github.Repository import Repository

from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE
from prdiffer.domain.entities.file_content import FileContentAvailable, FileContentResult, FileContentUnavailable
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.domain.services.github_api import GitHubAPIServiceInterface
from prdiffer.domain.services.pattern_matching import PatternMatchingServiceInterface
from prdiffer.domain.services.diff import DiffServiceInterface
from prdiffer.infrastructure.logging.console_logger import ConsoleLogger, get_logger
from prdiffer.infrastructure.utils.parallel.executor import (
    AsyncParallelExecutor,
)
from prdiffer.infrastructure.utils.parallel.results import ErrorStrategy


class FileProcessor:
    """Service for processing files in GitHub pull requests.

    This class handles file filtering, content loading, and parallel processing
    of files for diff generation using AsyncParallelExecutor for better performance.

    Thread Safety:
    - PR files cache access is protected by a reentrant lock
    - Prevents race condition in cache initialization and updates

    Async Support:
    - Parallel processing methods use AsyncParallelExecutor (anyio-based)
    - Maintains backward compatibility with sync methods
    """

    STATUS_TO_EDIT_TYPE: dict[str, EDIT_TYPE] = {
        "added": EDIT_TYPE.ADDED,
        "removed": EDIT_TYPE.DELETED,
        "renamed": EDIT_TYPE.RENAMED,
        "modified": EDIT_TYPE.MODIFIED,
    }

    def __init__(
        self,
        github_api_service: GitHubAPIServiceInterface,
        pattern_matcher: PatternMatchingServiceInterface,
        diff_utils: DiffServiceInterface,
        max_files_allowed: int = 50,
        parallel_fetch_threshold: int = 10,
        max_parallel_workers: int = 4,
        logger: ConsoleLogger | None = None,
        parallel_head_base_fetch_enabled: bool | None = None,
    ) -> None:
        self._github_api_service = github_api_service
        self._pattern_matcher = pattern_matcher
        self._diff_utils = diff_utils
        self.max_files_allowed = max_files_allowed
        self._parallel_fetch_threshold = parallel_fetch_threshold
        self._max_parallel_workers = max_parallel_workers
        self._logger = logger or get_logger()

        self._cache_lock = anyio.Lock()

        self._pr_files_cache: PaginatedList[File] | None = None
        self._pr_cache_timestamp: float = 0.0

        self._async_executor = AsyncParallelExecutor(
            max_concurrent=max_parallel_workers,
            error_strategy=ErrorStrategy.IGNORE,
            logger=logger,
        )

        if parallel_head_base_fetch_enabled is None:
            from prdiffer.infrastructure.settings import get_settings_service

            settings = get_settings_service()
            self._parallel_head_base_fetch_enabled = bool(
                settings.get("performance.parallel_head_base_fetch_enabled", False)
            )
        else:
            self._parallel_head_base_fetch_enabled = parallel_head_base_fetch_enabled

    async def get_pr_files(self, pull_request: PyGithubPullRequest) -> PaginatedList[File]:
        """Get all files from the pull request with caching (double-check locking, 5min TTL)."""
        if self._pr_files_cache is not None:
            current_time = time.time()
            if current_time - self._pr_cache_timestamp <= 300:
                return self._pr_files_cache

        async with self._cache_lock:
            current_time = time.time()
            if self._pr_files_cache is not None and current_time - self._pr_cache_timestamp <= 300:
                return self._pr_files_cache

            self._pr_files_cache = await asyncer.asyncify(pull_request.get_files)()
            self._pr_cache_timestamp = current_time
            assert self._pr_files_cache is not None
            return self._pr_files_cache

    def filter_files(self, files: Sequence[File]) -> list[File]:
        """Filter files based on pattern matching configuration."""
        return [file for file in files if self._pattern_matcher.is_valid_file(file.filename)]

    def _require_text(self, result: FileContentResult | str | None, *, path: str, ref: str) -> str:
        """Unwrap typed content; raise E5020 on deterministic unavailability.

        Accepts legacy bare strings from incomplete fakes during transition.
        """
        if result is None:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
                path=path,
            )
        if isinstance(result, str):
            return result
        if isinstance(result, FileContentAvailable):
            return result.text
        unavailable = cast(FileContentUnavailable, result)
        reason_map = {
            "BINARY_CONTENT": FullDiffIncompleteReason.BINARY_CONTENT,
            "FILE_SIZE_LIMIT": FullDiffIncompleteReason.FILE_SIZE_LIMIT,
            "DIRECTORY": FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
            "NOT_FOUND": FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
            "CONTENT_DECODE_FAILED": FullDiffIncompleteReason.CONTENT_DECODE_FAILED,
        }
        raise FullDiffIncompleteError(
            reason_map.get(unavailable.reason.value, FullDiffIncompleteReason.CONTENT_UNAVAILABLE),
            path=path,
            observed=unavailable.observed_size,
        )

    def _text_map(self, results: dict[str, Any], *, ref: str) -> dict[str, str]:
        """Convert typed batch results to path→text, raising on unavailable entries."""
        texts: dict[str, str] = {}
        for path, value in results.items():
            texts[path] = self._require_text(value, path=path, ref=ref)
        return texts

    def process_files_to_patches(self, files: list[File], repository: Repository, head_sha: str, base_sha: str) -> list[FilePatchInfo]:
        """Assemble FilePatchInfo list in provider order (strict, no soft skips)."""
        classified = self._classify_selected_files(files)
        if not classified:
            return []
        head_paths, base_paths, rename_map = self._required_content_keys(classified)
        head_raw = (
            self._github_api_service.get_files_content_batch(repository.full_name, head_paths, head_sha) if head_paths else {}
        )
        base_raw = (
            self._github_api_service.get_files_content_batch(repository.full_name, base_paths, base_sha) if base_paths else {}
        )
        head_contents = self._text_map(cast(dict[str, Any], head_raw), ref=head_sha)
        base_contents = self._text_map(cast(dict[str, Any], base_raw), ref=base_sha)
        return self._assemble_patches_in_order(classified, head_contents, base_contents, rename_map)

    async def process_files_to_patches_async(self, files: list[File], repository: Repository, head_sha: str, base_sha: str) -> list[FilePatchInfo]:
        """Async assembly with the same ordered strict semantics as the sync path."""
        classified = self._classify_selected_files(files)
        if not classified:
            return []
        head_paths, base_paths, rename_map = self._required_content_keys(classified)

        head_contents: dict[str, str] = {}
        base_contents: dict[str, str] = {}
        if head_paths:
            head_result = self._github_api_service.get_files_content_batch(repository.full_name, head_paths, head_sha)
            if inspect.iscoroutine(head_result):
                head_result = await head_result
            head_contents = self._text_map(cast(dict[str, Any], head_result), ref=head_sha)
        if base_paths:
            base_result = self._github_api_service.get_files_content_batch(repository.full_name, base_paths, base_sha)
            if inspect.iscoroutine(base_result):
                base_result = await base_result
            base_contents = self._text_map(cast(dict[str, Any], base_result), ref=base_sha)

        return self._assemble_patches_in_order(classified, head_contents, base_contents, rename_map)

    def _classify_selected_files(self, files: Sequence[File]) -> list[tuple[int, File, EDIT_TYPE]]:
        """Classify selected provider files with original indices; reject UNKNOWN."""
        classified: list[tuple[int, File, EDIT_TYPE]] = []
        for index, file in enumerate(files):
            if not self._pattern_matcher.is_valid_file(file.filename):
                continue
            status = getattr(file, "status", "") or ""
            edit_type = self.STATUS_TO_EDIT_TYPE.get(status, EDIT_TYPE.UNKNOWN)
            if edit_type is EDIT_TYPE.UNKNOWN:
                raise FullDiffIncompleteError(
                    FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
                    path=file.filename,
                )
            classified.append((index, file, edit_type))
        return classified

    def _required_content_keys(
        self,
        classified: list[tuple[int, File, EDIT_TYPE]],
    ) -> tuple[list[str], list[str], dict[str, str]]:
        """Build head/base path lists and rename base-path mapping."""
        head_paths: list[str] = []
        base_paths: list[str] = []
        rename_map: dict[str, str] = {}
        for _index, file, edit_type in classified:
            if edit_type in (EDIT_TYPE.ADDED, EDIT_TYPE.MODIFIED, EDIT_TYPE.RENAMED):
                head_paths.append(file.filename)
            if edit_type is EDIT_TYPE.MODIFIED:
                base_paths.append(file.filename)
            elif edit_type is EDIT_TYPE.DELETED:
                base_paths.append(file.filename)
            elif edit_type is EDIT_TYPE.RENAMED:
                previous_name = getattr(file, "previous_filename", None)
                base_key = previous_name if previous_name else file.filename
                base_paths.append(base_key)
                if previous_name:
                    rename_map[file.filename] = previous_name
        # Preserve order, drop duplicates while keeping first occurrence.
        def _unique(paths: list[str]) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []
            for path in paths:
                if path not in seen:
                    seen.add(path)
                    out.append(path)
            return out

        return _unique(head_paths), _unique(base_paths), rename_map

    def _assemble_patches_in_order(
        self,
        classified: list[tuple[int, File, EDIT_TYPE]],
        head_contents: dict[str, str],
        base_contents: dict[str, str],
        rename_map: dict[str, str],
    ) -> list[FilePatchInfo]:
        """Reconstruct FilePatchInfo rows in original provider order (no skips)."""
        # Sort by original index to preserve provider order even if input shuffled.
        ordered = sorted(classified, key=lambda item: item[0])
        results: list[FilePatchInfo] = []
        for _index, file, edit_type in ordered:
            if edit_type is EDIT_TYPE.ADDED:
                original = ""
                new = head_contents.get(file.filename, "")
            elif edit_type is EDIT_TYPE.DELETED:
                original = base_contents.get(file.filename, "")
                new = ""
            elif edit_type is EDIT_TYPE.RENAMED:
                base_key = rename_map.get(file.filename, file.filename)
                original = base_contents.get(base_key, "")
                new = head_contents.get(file.filename, "")
            else:  # MODIFIED
                original = base_contents.get(file.filename, "")
                new = head_contents.get(file.filename, "")

            patch = file.patch or ""
            if not patch:
                patch = self._generate_patch_from_content(file.filename, new, original)

            results.append(
                self._create_file_patch_with_content(
                    file,
                    original,
                    new,
                    patch,
                    edit_type=edit_type,
                    old_filename=rename_map.get(file.filename) if edit_type is EDIT_TYPE.RENAMED else None,
                )
            )
        return results

    async def _process_files_with_content_parallel_async(
        self,
        files: list[File],
        repository: Repository,
        head_sha: str,
        base_sha: str,
    ) -> list[FilePatchInfo]:
        """Process files with parallel content loading using AsyncParallelExecutor."""
        start_time = time.time()
        diff_files: list[FilePatchInfo] = []

        head_files: list[str] = []
        base_files: list[str] = []
        renamed_file_mapping: dict[str, str] = {}

        for file in files:
            if file.status in ["added", "modified", "renamed"]:
                head_files.append(file.filename)
            if file.status == "modified":
                base_files.append(file.filename)
            elif file.status == "renamed":
                previous_name = getattr(file, "previous_filename", None)
                if previous_name:
                    base_files.append(previous_name)
                    renamed_file_mapping[file.filename] = previous_name
                else:
                    base_files.append(file.filename)

        fetch_tasks: list[Any] = []
        if head_files:
            fetch_tasks.append(self._github_api_service.get_files_content_batch(repository.full_name, head_files, head_sha))
        else:
            fetch_tasks.append(anyio.sleep(0))

        if base_files:
            fetch_tasks.append(self._github_api_service.get_files_content_batch(repository.full_name, base_files, base_sha))
        else:
            fetch_tasks.append(anyio.sleep(0))

        head_contents: dict[str, str] = {}
        base_contents: dict[str, str] = {}
        try:
            head_result: Any = fetch_tasks[0] if head_files else {}
            if inspect.iscoroutine(head_result):
                head_result = await head_result
            if isinstance(head_result, dict):
                head_contents = self._text_map(cast(dict[str, Any], head_result), ref=head_sha)

            base_result: Any = fetch_tasks[1] if base_files else {}
            if inspect.iscoroutine(base_result):
                base_result = await base_result
            if isinstance(base_result, dict):
                base_contents = self._text_map(cast(dict[str, Any], base_result), ref=base_sha)
        except FullDiffIncompleteError:
            raise
        except (AttributeError, TypeError) as e:
            self._logger.warning(
                "Tasks not awaitable, using empty contents",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "has_head_files": bool(head_files),
                    "has_base_files": bool(base_files),
                },
            )
            head_contents = {}
            base_contents = {}

        for file in files:
            if file.status == "added":
                new_file_content = head_contents.get(file.filename, "")
                original_file_content = ""
            elif file.status == "removed":
                self._logger.info(f"Skipping deleted file: {file.filename}")
                continue
            elif file.status == "renamed":
                new_file_content = head_contents.get(file.filename, "")
                base_key = renamed_file_mapping.get(file.filename, file.filename)
                original_file_content = base_contents.get(base_key, "")

                if self._is_rename_only(file, original_file_content, new_file_content):
                    previous_name = getattr(file, "previous_filename", "?")
                    self._logger.info(f"Skipping rename-only file: {previous_name} -> {file.filename}")
                    continue
            else:  # modified or other statuses
                new_file_content = head_contents.get(file.filename, "")
                original_file_content = base_contents.get(file.filename, "")

            patch = file.patch
            if not patch:
                patch = self._generate_patch_from_content(file.filename, new_file_content, original_file_content)

            file_patch = self._create_file_patch_with_content(file, original_file_content, new_file_content, patch)
            diff_files.append(file_patch)

        elapsed = time.time() - start_time
        self._logger.debug(f"Async parallel content processing: {len(files)} files in {elapsed:.2f}s")

        return diff_files

    def _process_files_with_content(self, files: list[File], repository: Repository, head_sha: str, base_sha: str) -> list[FilePatchInfo]:
        """Process files with content loading (batch mode, synchronous)."""
        diff_files: list[FilePatchInfo] = []

        head_files: list[str] = []
        base_files: list[str] = []
        renamed_file_mapping: dict[str, str] = {}

        for file in files:
            if file.status in ["added", "modified", "renamed"]:
                head_files.append(file.filename)
            if file.status == "modified":
                base_files.append(file.filename)
            elif file.status == "renamed":
                previous_name = getattr(file, "previous_filename", None)
                if previous_name:
                    base_files.append(previous_name)
                    renamed_file_mapping[file.filename] = previous_name
                else:
                    base_files.append(file.filename)

        head_raw = (
            self._github_api_service.get_files_content_batch(repository.full_name, head_files, head_sha) if head_files else {}
        )
        base_raw = (
            self._github_api_service.get_files_content_batch(repository.full_name, base_files, base_sha) if base_files else {}
        )
        head_contents = self._text_map(cast(dict[str, Any], head_raw), ref=head_sha)
        base_contents = self._text_map(cast(dict[str, Any], base_raw), ref=base_sha)

        for file in files:
            if file.status == "added":
                new_file_content = head_contents.get(file.filename, "")
                original_file_content = ""
            elif file.status == "removed":
                self._logger.info(f"Skipping deleted file: {file.filename}")
                continue
            elif file.status == "renamed":
                new_file_content = head_contents.get(file.filename, "")
                base_key = renamed_file_mapping.get(file.filename, file.filename)
                original_file_content = base_contents.get(base_key, "")

                if self._is_rename_only(file, original_file_content, new_file_content):
                    previous_name = getattr(file, "previous_filename", "?")
                    self._logger.info(f"Skipping rename-only file: {previous_name} -> {file.filename}")
                    continue
            else:  # modified or other statuses
                new_file_content = head_contents.get(file.filename, "")
                original_file_content = base_contents.get(file.filename, "")

            patch = file.patch
            if not patch:
                patch = self._generate_patch_from_content(file.filename, new_file_content, original_file_content)

            file_patch = self._create_file_patch_with_content(file, original_file_content, new_file_content, patch)
            diff_files.append(file_patch)

        return diff_files

    def _create_file_patch_without_content(self, file: File) -> FilePatchInfo:
        """Create FilePatchInfo without loading file content."""
        edit_type = self.STATUS_TO_EDIT_TYPE.get(file.status, EDIT_TYPE.UNKNOWN)
        if edit_type == EDIT_TYPE.UNKNOWN:
            self._logger.error(f"Unknown edit type: {file.status}")

        patch = file.patch or ""
        num_plus_lines, num_minus_lines = self._count_patch_lines(file, patch)

        return FilePatchInfo(
            base_file="",
            head_file="",
            patch=patch,
            filename=file.filename,
            edit_type=edit_type,
            num_plus_lines=num_plus_lines,
            num_minus_lines=num_minus_lines,
        )

    def _create_file_patch_with_content(
        self,
        file: File,
        original_content: str,
        new_content: str,
        patch: str,
        *,
        edit_type: EDIT_TYPE | None = None,
        old_filename: str | None = None,
    ) -> FilePatchInfo:
        """Create FilePatchInfo with loaded file content."""
        resolved_type = edit_type or self.STATUS_TO_EDIT_TYPE.get(file.status, EDIT_TYPE.UNKNOWN)
        if resolved_type is EDIT_TYPE.UNKNOWN:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
                path=file.filename,
            )

        num_plus_lines, num_minus_lines = self._count_patch_lines(file, patch)
        previous = old_filename
        if previous is None and resolved_type is EDIT_TYPE.RENAMED:
            previous = getattr(file, "previous_filename", None)

        return FilePatchInfo(
            base_file=original_content,
            head_file=new_content,
            patch=patch,
            filename=file.filename,
            edit_type=resolved_type,
            old_filename=previous,
            num_plus_lines=num_plus_lines,
            num_minus_lines=num_minus_lines,
        )

    def _count_patch_lines(self, file: File, patch: str) -> tuple[int, int]:
        """Count added and removed lines from file or patch."""
        if hasattr(file, "additions") and hasattr(file, "deletions"):
            return file.additions, file.deletions

        if patch:
            patch_lines = patch.splitlines(keepends=True)
            num_plus_lines = sum(1 for line in patch_lines if line.startswith("+"))
            num_minus_lines = sum(1 for line in patch_lines if line.startswith("-"))
            return num_plus_lines, num_minus_lines

        return 0, 0

    def _generate_patch_from_content(self, filename: str, new_content: str, original_content: str) -> str:
        """Generate a patch for a file by comparing content."""
        if not original_content and not new_content:
            return ""

        try:
            import difflib

            original_content = (original_content or "").rstrip() + "\n"
            new_content = (new_content or "").rstrip() + "\n"
            diff = difflib.unified_diff(
                original_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
            )
            self._logger.info(f"File was modified, but no patch was found. Manually creating patch: {filename}.")
            patch = "".join(diff)
            return patch
        except TypeError, ValueError, AttributeError:
            self._logger.error(f"Failed to generate patch for file: {filename}")
            return ""

    def _is_rename_only(self, file: File, original_content: str = "", new_content: str = "") -> bool:
        """Check if a renamed file has no content changes (API metadata primary, content comparison fallback)."""
        if hasattr(file, "additions") and hasattr(file, "deletions"):
            if file.additions == 0 and file.deletions == 0:
                self._logger.debug(f"Rename-only detected via API metadata: {file.filename}")
                return True
            return False

        if original_content and new_content:
            is_identical = original_content.rstrip() == new_content.rstrip()
            if is_identical:
                self._logger.debug(f"Rename-only detected via content comparison: {file.filename}")
            return is_identical

        # If no content available, cannot determine - assume has changes (conservative)
        return False


def get_file_processor(
    github_api_service: GitHubAPIServiceInterface,
    pattern_matcher: PatternMatchingServiceInterface,
    diff_utils: DiffServiceInterface,
    max_files_allowed: int = 50,
    parallel_fetch_threshold: int = 10,
    max_parallel_workers: int = 4,
) -> FileProcessor:
    """Get a configured file processor instance."""
    return FileProcessor(
        github_api_service=github_api_service,
        pattern_matcher=pattern_matcher,
        diff_utils=diff_utils,
        max_files_allowed=max_files_allowed,
        parallel_fetch_threshold=parallel_fetch_threshold,
        max_parallel_workers=max_parallel_workers,
    )
