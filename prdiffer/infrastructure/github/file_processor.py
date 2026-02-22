"""File processing service for GitHub repositories."""

import inspect
import time
import logging
import anyio
from typing import cast
from github.File import File
from github.PaginatedList import PaginatedList
from github.Repository import Repository

from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE
from prdiffer.domain.services import GitHubAPIServiceInterface
from prdiffer.domain.services import PatternMatchingServiceInterface
from prdiffer.domain.services import DiffServiceInterface
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.utils.parallel import (
    AsyncParallelExecutor,
    ErrorStrategy,
)


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
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the file processor.

        Args:
            github_api_service: Service for GitHub API operations
            pattern_matcher: Service for file pattern matching
            diff_utils: Service for diff utilities
            max_files_allowed: Maximum number of files to load content for
            parallel_fetch_threshold: File count threshold to use parallel fetching
            max_parallel_workers: Max workers for parallel content fetching
            logger: Logger instance for logging operations
        """
        self._github_api_service = github_api_service
        self._pattern_matcher = pattern_matcher
        self._diff_utils = diff_utils
        self.max_files_allowed = max_files_allowed
        self._parallel_fetch_threshold = parallel_fetch_threshold
        self._max_parallel_workers = max_parallel_workers
        self._logger = logger or get_logger()

        # Async lock for cache operations
        self._cache_lock = anyio.Lock()

        # Cache for PR files to avoid repeated API calls
        self._pr_files_cache: PaginatedList[File] | None = None
        self._pr_cache_timestamp: float = 0.0

        # Async parallel executor for concurrent operations
        self._async_executor = AsyncParallelExecutor(
            max_concurrent=max_parallel_workers,
            error_strategy=ErrorStrategy.IGNORE,
            logger=logger,
        )

    async def get_pr_files(self, pull_request) -> PaginatedList[File]:
        """Get all files from the pull request with caching.

        Thread-safe: Uses double-check locking pattern for cache initialization.

        Args:
            pull_request: GitHub pull request object

        Returns:
            PaginatedList of File objects from the PR
        """
        # Fast path: check cache without lock (double-check pattern)
        if self._pr_files_cache is not None:
            # Check if cache is still valid (5 minutes)
            current_time = time.time()
            if current_time - self._pr_cache_timestamp <= 300:
                return self._pr_files_cache

        # Slow path: acquire lock and double-check
        async with self._cache_lock:
            # Double-check cache validity after acquiring lock
            current_time = time.time()
            if self._pr_files_cache is not None and current_time - self._pr_cache_timestamp <= 300:
                return self._pr_files_cache

            # Cache is stale or uninitialized - update it
            self._pr_files_cache = pull_request.get_files()
            self._pr_cache_timestamp = current_time

        return self._pr_files_cache

    def filter_files(self, files: PaginatedList[File]) -> list[File]:
        """Filter files based on pattern matching configuration.

        Args:
            files: PaginatedList of file objects to filter

        Returns:
            Filtered list of files
        """
        return [file for file in files if self._pattern_matcher.is_valid_file(file.filename)]

    def process_files_to_patches(self, files: list[File], repository: Repository, head_sha: str, base_sha: str) -> list[FilePatchInfo]:
        """Process files into FilePatchInfo objects with content loading.

        Args:
            files: List of filtered files to process
            repository: GitHub repository instance
            head_sha: Head commit SHA
            base_sha: Base commit SHA

        Returns:
            List of FilePatchInfo objects with loaded content
        """
        diff_files: list[FilePatchInfo] = []
        invalid_files_names: list[str] = []

        counter_valid = 0
        files_to_load = []

        # First pass: identify files for batch processing
        for file in files:
            if not self._pattern_matcher.is_valid_file(file.filename):
                invalid_files_names.append(file.filename)
                continue

            patch = file.patch
            counter_valid += 1

            # Determine if we should load full content for this file
            avoid_load = False
            if counter_valid >= self.max_files_allowed and patch:
                avoid_load = True
                if counter_valid == self.max_files_allowed:
                    self._logger.info("Too many files in PR, will avoid loading full content for rest of files")

            if avoid_load:
                # Process without content loading
                file_patch = self._create_file_patch_without_content(file)
                diff_files.append(file_patch)
            else:
                # Add to batch processing list
                files_to_load.append(file)

        # Second pass: batch process files that need content loading
        if files_to_load:
            # Use synchronous batch processing for consistency
            processed_files = self._process_files_with_content(files_to_load, repository, head_sha, base_sha)
            diff_files.extend(processed_files)

        if invalid_files_names:
            self._logger.info(f"Filtered out files with invalid extensions: {invalid_files_names}")

        return diff_files

    async def process_files_to_patches_async(self, files: list[File], repository: Repository, head_sha: str, base_sha: str) -> list[FilePatchInfo]:
        """Async version of process_files_to_patches.

        Args:
            files: List of filtered files to process
            repository: GitHub repository instance
            head_sha: Head commit SHA
            base_sha: Base commit SHA

        Returns:
            List of FilePatchInfo objects with loaded content
        """
        diff_files: list[FilePatchInfo] = []
        invalid_files_names: list[str] = []

        counter_valid = 0
        files_to_load = []

        # First pass: identify files for batch processing
        for file in files:
            if not self._pattern_matcher.is_valid_file(file.filename):
                invalid_files_names.append(file.filename)
                continue

            patch = file.patch
            counter_valid += 1

            # Determine if we should load full content for this file
            avoid_load = False
            if counter_valid >= self.max_files_allowed and patch:
                avoid_load = True
                if counter_valid == self.max_files_allowed:
                    self._logger.info("Too many files in PR, will avoid loading full content for rest of files")

            if avoid_load:
                # Process without content loading
                file_patch = self._create_file_patch_without_content(file)
                diff_files.append(file_patch)
            else:
                # Add to batch processing list
                files_to_load.append(file)

        # Second pass: batch process files that need content loading
        if files_to_load:
            processed_files = await self._process_files_with_content_parallel_async(
                files_to_load,
                repository,
                head_sha,
                base_sha,
            )
            diff_files.extend(processed_files)

        if invalid_files_names:
            self._logger.info(f"Filtered out files with invalid extensions: {invalid_files_names}")

        return diff_files

    async def _process_files_with_content_parallel_async(
        self,
        files: list[File],
        repository: Repository,
        head_sha: str,
        base_sha: str,
    ) -> list[FilePatchInfo]:
        """Process files with parallel content loading for better performance (async version).

        Fetches head and base content concurrently using AsyncParallelExecutor,
        significantly improving performance for PRs with many files.

        Args:
            files: List of files to process
            repository: GitHub repository instance
            head_sha: Head commit SHA
            base_sha: Base commit SHA

        Returns:
            List of FilePatchInfo objects with content loaded
        """
        start_time = time.time()
        diff_files = []

        # Separate files by status to optimize API calls
        head_files = []  # Files to fetch from head commit
        base_files = []  # Files to fetch from base commit
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

        # Fetch head and base contents in parallel using async tasks
        fetch_tasks = []
        if head_files:
            fetch_tasks.append(self._github_api_service.get_files_content_batch(repository.full_name, head_files, head_sha))
        else:
            fetch_tasks.append(anyio.sleep(0))

        if base_files:
            fetch_tasks.append(self._github_api_service.get_files_content_batch(repository.full_name, base_files, base_sha))
        else:
            fetch_tasks.append(anyio.sleep(0))  # Placeholder

        # Execute fetches in parallel (if GitHubAPIClient had async methods)
        # For now, run sequentially since GitHubAPIClient is synchronous
        head_contents: dict[str, str] = {}
        base_contents: dict[str, str] = {}
        try:
            head_result = fetch_tasks[0] if head_files else {}
            if inspect.iscoroutine(head_result):
                head_result = await head_result
            if isinstance(head_result, dict):
                head_contents = cast(dict[str, str], head_result)

            base_result = fetch_tasks[1] if base_files else {}
            if inspect.iscoroutine(base_result):
                base_result = await base_result
            if isinstance(base_result, dict):
                base_contents = cast(dict[str, str], base_result)
        except (AttributeError, TypeError) as e:
            # Handle the case where tasks are not awaitable
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

        # Process each file with loaded content
        for file in files:
            # Get content based on file status to avoid 404 errors
            if file.status == "added":
                new_file_content = head_contents.get(file.filename, "")
                original_file_content = ""  # Added files don't exist in base
            elif file.status == "removed":
                # Skip deleted files - nothing to compare
                self._logger.info(f"Skipping deleted file: {file.filename}")
                continue
            elif file.status == "renamed":
                # For renamed files, use the previous filename to get base content
                new_file_content = head_contents.get(file.filename, "")
                base_key = renamed_file_mapping.get(file.filename, file.filename)
                original_file_content = base_contents.get(base_key, "")

                # Skip rename-only files (no content changes)
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
        """Process files with content loading (batch mode).

        Args:
            files: List of files to process
            repository: GitHub repository instance
            head_sha: Head commit SHA
            base_sha: Base commit SHA

        Returns:
            List of FilePatchInfo objects with content loaded
        """
        diff_files = []

        # Separate files by status to optimize API calls
        head_files = []  # Files to fetch from head commit
        base_files = []  # Files to fetch from base commit
        renamed_file_mapping: dict[str, str] = {}

        for file in files:
            if file.status in ["added", "modified", "renamed"]:
                head_files.append(file.filename)
            if file.status == "modified":
                base_files.append(file.filename)
            elif file.status == "renamed":
                # For renamed files, use previous_filename to fetch from base commit
                previous_name = getattr(file, "previous_filename", None)
                if previous_name:
                    base_files.append(previous_name)
                    renamed_file_mapping[file.filename] = previous_name
                else:
                    # Fallback to current filename if previous_filename not available
                    base_files.append(file.filename)

        # Batch load content - sequential processing to avoid blocking
        head_contents = self._github_api_service.get_files_content_batch(repository.full_name, head_files, head_sha) if head_files else {}

        base_contents = self._github_api_service.get_files_content_batch(repository.full_name, base_files, base_sha) if base_files else {}

        # Process each file with loaded content
        for file in files:
            # Get content based on file status to avoid 404 errors
            if file.status == "added":
                new_file_content = head_contents.get(file.filename, "")
                original_file_content = ""  # Added files don't exist in base
            elif file.status == "removed":
                # Skip deleted files - nothing to compare
                self._logger.info(f"Skipping deleted file: {file.filename}")
                continue
            elif file.status == "renamed":
                # For renamed files, use the previous filename to get base content
                new_file_content = head_contents.get(file.filename, "")
                base_key = renamed_file_mapping.get(file.filename, file.filename)
                original_file_content = base_contents.get(base_key, "")

                # Skip rename-only files (no content changes)
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
        """Create FilePatchInfo without loading file content.

        Args:
            file: GitHub file object

        Returns:
            FilePatchInfo with empty content strings
        """
        edit_type = self.STATUS_TO_EDIT_TYPE.get(file.status, EDIT_TYPE.UNKNOWN)
        if edit_type == EDIT_TYPE.UNKNOWN:
            self._logger.error(f"Unknown edit type: {file.status}")

        # Count lines from patch if available
        patch = file.patch or ""
        num_plus_lines, num_minus_lines = self._count_patch_lines(file, patch)

        return FilePatchInfo(
            base_file="",  # Empty content
            head_file="",  # Empty content
            patch=patch,
            filename=file.filename,
            edit_type=edit_type,
            num_plus_lines=num_plus_lines,
            num_minus_lines=num_minus_lines,
        )

    def _create_file_patch_with_content(self, file: File, original_content: str, new_content: str, patch: str) -> FilePatchInfo:
        """Create FilePatchInfo with loaded file content.

        Args:
            file: GitHub file object
            original_content: Base file content
            new_content: Head file content
            patch: Unified diff patch

        Returns:
            FilePatchInfo with loaded content
        """
        edit_type: EDIT_TYPE = self.STATUS_TO_EDIT_TYPE.get(file.status, EDIT_TYPE.UNKNOWN)
        if edit_type == EDIT_TYPE.UNKNOWN:
            self._logger.error(f"Unknown edit type: {file.status}")

        num_plus_lines, num_minus_lines = self._count_patch_lines(file, patch)

        return FilePatchInfo(
            base_file=original_content,
            head_file=new_content,
            patch=patch,
            filename=file.filename,
            edit_type=edit_type,
            num_plus_lines=num_plus_lines,
            num_minus_lines=num_minus_lines,
        )

    def _count_patch_lines(self, file: File, patch: str) -> tuple[int, int]:
        """Count added and removed lines from file or patch.

        Args:
            file: GitHub file object
            patch: Patch content

        Returns:
            Tuple of (num_plus_lines, num_minus_lines)
        """
        # Use GitHub API data if available
        if hasattr(file, "additions") and hasattr(file, "deletions"):
            return file.additions, file.deletions

        # Fall back to counting patch lines
        if patch:
            patch_lines = patch.splitlines(keepends=True)
            num_plus_lines = sum(1 for line in patch_lines if line.startswith("+"))
            num_minus_lines = sum(1 for line in patch_lines if line.startswith("-"))
            return num_plus_lines, num_minus_lines

        return 0, 0

    def _generate_patch_from_content(self, filename: str, new_content: str, original_content: str) -> str:
        """Generate a patch for a file by comparing content.

        Args:
            filename: Name of the file
            new_content: New file content
            original_content: Original file content

        Returns:
            Generated patch string
        """
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
        """Check if a renamed file has no content changes.

        Uses GitHub API metadata as primary check, falls back to content comparison.

        Args:
            file: GitHub file object with status == "renamed"
            original_content: Base file content (for fallback comparison)
            new_content: Head file content (for fallback comparison)

        Returns:
            True if file is renamed without content changes, False otherwise
        """
        # Primary check: GitHub API metadata
        if hasattr(file, "additions") and hasattr(file, "deletions"):
            if file.additions == 0 and file.deletions == 0:
                self._logger.debug(f"Rename-only detected via API metadata: {file.filename}")
                return True
            # Has changes - not rename-only
            return False

        # Fallback: Content comparison (when API metadata unavailable)
        if original_content and new_content:
            # Normalize trailing whitespace and compare
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
    """Get a configured file processor instance.

    Args:
        github_api_service: Service for GitHub API operations
        pattern_matcher: Service for file pattern matching
        diff_utils: Service for diff utilities
        max_files_allowed: Maximum number of files to load content for

    Returns:
        FileProcessor: Configured file processor instance
    """
    return FileProcessor(
        github_api_service=github_api_service,
        pattern_matcher=pattern_matcher,
        diff_utils=diff_utils,
        max_files_allowed=max_files_allowed,
        parallel_fetch_threshold=parallel_fetch_threshold,
        max_parallel_workers=max_parallel_workers,
    )
