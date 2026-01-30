"""Infrastructure implementation of PRDiffServiceInterface.

This module provides the concrete implementation of PRDiffServiceInterface
using GitHub API operations.
"""

import os
from typing import Optional, Tuple, Type, cast

import asyncer
from github import GithubException
from prdiffer.domain.services.pr_diff_service import PRDiffServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE
from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.infrastructure.github.api_client import GitHubAPIClient
from prdiffer.infrastructure.github.diff_generator import DiffGenerator
from prdiffer.infrastructure.github.file_processor import FileProcessor
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)
from prdiffer.infrastructure.security.input_validator import InputValidator
from prdiffer.infrastructure.settings import get_settings_service
from prdiffer.infrastructure.utils.cache_decorator import (
    CachingMixin,
    cached_method,
)


# Exceptions to catch in PR diff service operations
# Note: We deliberately exclude KeyboardInterrupt, SystemExit, and GeneratorExit
# to allow system-level exceptions to propagate for proper shutdown/cleanup.
PR_SERVICE_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
    # GitHub-specific exceptions
    GithubException,
    # Network and timeout exceptions
    TimeoutError,
    ConnectionError,
    OSError,
    # Common runtime exceptions
    RuntimeError,
    ValueError,
    TypeError,
)


class GitHubPRDiffService(CachingMixin, PRDiffServiceInterface):
    """Concrete implementation of PRDiffServiceInterface using GitHub API.

    Features:
    - PR diff retrieval with commit-based caching at use case level
    - Method-level caching with TTL for performance optimization
    - Thread-safe caching with reentrant lock protection
    """

    def __init__(
        self,
        github_api_client: Optional[GitHubAPIClient] = None,
        diff_generator: Optional[DiffGenerator] = None,
        file_processor: Optional[FileProcessor] = None,
        logger: Optional[LoggerServiceInterface] = None,
    ):
        """Initialize the service with GitHub API client and diff generation components.

        Args:
            github_api_client: Optional GitHub API client (created if None)
            diff_generator: Optional diff generator (created if None)
            file_processor: Optional file processor (created if None)
            logger: Optional logger instance
        """
        # Initialize caching mixin with 5-minute TTL and 1000 entry cache
        super().__init__(max_cache_size=1000, default_ttl=300)

        self._github_api: GitHubAPIClient = github_api_client or GitHubAPIClient()
        self._logger = logger or get_logger()

        # Initialize the GitHub client with environment variables and settings
        github_token = os.getenv("GITHUB_TOKEN")
        timeout = int(os.getenv("GITHUB_TIMEOUT", "30"))

        self._github_api.initialize_client(github_token=github_token, timeout=timeout)

        # Initialize diff generation components
        self._diff_generator = diff_generator
        self._file_processor = file_processor

        settings_service = get_settings_service()
        self._diff_truncate_enabled = settings_service.get(
            "diff.truncate_enabled", False
        )
        self._diff_max_total_chars = int(
            settings_service.get("diff.max_total_chars", 200000)
        )
        self._diff_truncation_notice = settings_service.get(
            "diff.truncation_notice", "[DIFF TRUNCATED]"
        )

    async def get_pr_diff(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> Optional[PRDiff]:
        """Get PR diff data for the specified repository and PR.

        This implementation uses native async with the async file processor
        for improved performance on multi-file PRs.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            Optional[PRDiff]: PR diff data if successful, None otherwise

        Raises:
            RepositoryNotFoundError: If repository or PR doesn't exist
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            ValidationError: If input parameters are invalid
        """
        # Try to use async file processing if available (better performance)
        if self._file_processor and hasattr(
            self._file_processor, "process_files_to_patches_async"
        ):
            return await self._get_pr_diff_async_native(
                repo_owner, repo_name, pr_number
            )

        # Fallback to sync-to-async wrapper for backward compatibility
        return await asyncer.asyncify(self._get_pr_diff_sync)(
            repo_owner, repo_name, pr_number
        )

    async def _get_pr_diff_async_native(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> Optional[PRDiff]:
        """Get PR diff data using native async implementation with parallel file processing.

        This method provides better performance for PRs with multiple files by:
        - Using async file processor with parallel content fetching
        - Leveraging AsyncParallelExecutor for concurrent operations
        - Reducing overall latency through parallelization

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            Optional[PRDiff]: PR diff data if successful, None otherwise
        """
        try:
            # Use the GitHub API client to get repository and PR
            repository = self._github_api._get_pygithub_repository(
                f"{repo_owner}/{repo_name}"
            )
            if not repository:
                return None

            pull_request = self._github_api._get_pygithub_pull_request(
                repository, pr_number
            )
            if not pull_request:
                return None

            # Generate diff content using async parallel processing
            _, diff_files = await self._generate_diff_content_async(
                repository, pull_request
            )

            # Convert FilePatchInfo list to FileDiffResponse list
            file_responses = [
                self._convert_file_patch_info_to_response(file_patch)
                for file_patch in diff_files
            ]

            pr_diff = PRDiff(files=file_responses)

            self._logger.info(
                "Generated diff content (async parallel)",
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                num_files=len(file_responses),
            )

            preview = InputValidator.sanitize_for_logging(
                f"Files: {len(file_responses)}", max_length=1000
            )
            self._logger.debug("Diff content preview", preview=preview)

            return pr_diff

        except PR_SERVICE_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(
                "Failed to get PR diff (async)",
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                extra=sanitized,
            )
            return None

    async def _generate_diff_content_async(
        self, repository, pull_request
    ) -> tuple[str, list[FilePatchInfo]]:
        """Generate diff content for the pull request using async parallel processing.

        This method uses the async file processor for parallel content fetching,
        providing better performance for PRs with multiple files.

        Args:
            repository: GitHub repository instance
            pull_request: GitHub pull request instance

        Returns:
            tuple[str, list[FilePatchInfo]]: Combined diff content and file metadata,
            empty string/list on error
        """
        try:
            # Get the latest commit SHA for the PR
            latest_commit_sha = pull_request.head.sha
            if not latest_commit_sha:
                return "", []

            # Get the base commit SHA (merge base)
            base_commit_sha = self._get_base_commit_sha(repository, pull_request)
            if not base_commit_sha:
                return "", []

            # Get and process files
            github_files = pull_request.get_files()
            if not github_files:
                return "", []

            # Use async file processor for parallel content fetching
            if self._file_processor and hasattr(
                self._file_processor, "process_files_to_patches_async"
            ):
                # Async parallel processing for better performance
                diff_files = await self._file_processor.process_files_to_patches_async(
                    list(github_files), repository, latest_commit_sha, base_commit_sha
                )
            else:
                # Fallback to sync processing
                diff_files = (
                    self._file_processor.process_files_to_patches(
                        list(github_files),
                        repository,
                        latest_commit_sha,
                        base_commit_sha,
                    )
                    if self._file_processor
                    else self._convert_github_files_to_file_patch_info(github_files)
                )

            # Generate extended diff content
            if self._diff_generator and diff_files:
                extended_diffs = self._diff_generator.generate_extended_diff(diff_files)
                return "\n".join(extended_diffs), diff_files
            else:
                # Fallback: create simple diff from patches
                diff_content_parts = []
                for file_patch in diff_files:
                    if file_patch.patch:
                        diff_content_parts.append(
                            f"## File: {file_patch.filename}\n{file_patch.patch}"
                        )
                return "\n\n".join(diff_content_parts), diff_files

        except PR_SERVICE_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(
                "Failed to generate diff content (async)", extra=sanitized
            )
            return "", []

    async def get_latest_commit_sha(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> Optional[str]:
        """Get the latest head commit SHA for the pull request.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            Optional[str]: Latest commit SHA if successful, None otherwise

        Raises:
            RepositoryNotFoundError: If repository or PR doesn't exist
            AuthenticationError: If authentication fails
        """
        return await asyncer.asyncify(self._get_latest_commit_sha_sync)(
            repo_owner, repo_name, pr_number
        )

    @cached_method(ttl=300, key_prefix="pr_diff")
    def _get_pr_diff_sync(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> Optional[PRDiff]:
        """Get PR diff data synchronously with method-level caching.

        Caching:
        - Results are cached for 5 minutes (300 seconds)
        - Cache key includes repo_owner, repo_name, and pr_number
        - Cache is automatically invalidated after TTL expires
        - Use case-level commit-based caching provides additional freshness

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            Optional[PRDiff]: PR diff data if successful, None otherwise
        """
        try:
            # Use the GitHub API client to get repository and PR
            repository = self._github_api._get_pygithub_repository(
                f"{repo_owner}/{repo_name}"
            )
            if not repository:
                return None

            pull_request = self._github_api._get_pygithub_pull_request(
                repository, pr_number
            )
            if not pull_request:
                return None

            # Generate diff content
            diff_files = self._generate_diff_content(repository, pull_request)

            # Convert FilePatchInfo list to FileDiffResponse list
            file_responses = [
                self._convert_file_patch_info_to_response(file_patch)
                for file_patch in diff_files
            ]

            pr_diff = PRDiff(files=file_responses)

            self._logger.info(
                "Generated diff content",
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                num_files=len(file_responses),
            )

            preview = InputValidator.sanitize_for_logging(
                f"Files: {len(file_responses)}", max_length=1000
            )
            self._logger.debug("Diff content preview", preview=preview)

            return pr_diff

        except PR_SERVICE_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(
                "Failed to get PR diff",
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                extra=sanitized,
            )
            return None

    def _get_latest_commit_sha_sync(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> Optional[str]:
        try:
            repository = self._github_api._get_pygithub_repository(
                f"{repo_owner}/{repo_name}"
            )
            if not repository:
                return None

            pull_request = self._github_api._get_pygithub_pull_request(
                repository, pr_number
            )
            if not pull_request:
                return None

            return pull_request.head.sha

        except PR_SERVICE_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(
                "Failed to get latest commit SHA",
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                extra=sanitized,
            )
            return None

    def _convert_github_files_to_file_patch_info(self, github_files):
        """Convert GitHub File objects to FilePatchInfo domain entities.

        Args:
            github_files: List of GitHub File objects from PyGithub

        Returns:
            List of FilePatchInfo objects
        """
        file_patch_infos = []

        for github_file in github_files:
            # Map GitHub file status to EDIT_TYPE
            edit_type = self._map_github_status_to_edit_type(github_file.status)

            # Get file content if available (for now, we'll use empty strings)
            # In a full implementation, we would fetch the actual file content
            base_file = ""
            head_file = ""

            # Create FilePatchInfo object
            file_patch_info = FilePatchInfo(
                filename=github_file.filename,
                base_file=base_file,
                head_file=head_file,
                patch=github_file.patch or "",
                edit_type=edit_type,
                num_plus_lines=github_file.additions or 0,
                num_minus_lines=github_file.deletions or 0,
            )

            file_patch_infos.append(file_patch_info)

        return file_patch_infos

    def _map_github_status_to_edit_type(self, status: str) -> EDIT_TYPE:
        """Map GitHub file status to EDIT_TYPE enum.

        Args:
            status: GitHub file status (added, removed, modified, renamed)

        Returns:
            EDIT_TYPE enum value
        """
        status_mapping = {
            "added": EDIT_TYPE.ADDED,
            "removed": EDIT_TYPE.DELETED,
            "modified": EDIT_TYPE.MODIFIED,
            "renamed": EDIT_TYPE.RENAMED,
        }

        return status_mapping.get(status, EDIT_TYPE.UNKNOWN)

    def _convert_file_patch_info_to_response(
        self, file_patch: FilePatchInfo
    ) -> FileDiffResponse:
        """Convert FilePatchInfo to FileDiffResponse for PRDiff structure.

        Field mapping from FilePatchInfo to FileDiffResponse:
        - filename → path
        - edit_type → status
        - num_plus_lines → stats.additions
        - num_minus_lines → stats.deletions
        - patch → diff

        Args:
            file_patch: FilePatchInfo object from domain layer

        Returns:
            FileDiffResponse: Converted object for structured response
        """
        stats = FileStats(
            additions=file_patch.num_plus_lines, deletions=file_patch.num_minus_lines
        )
        return FileDiffResponse(
            path=file_patch.filename,
            status=file_patch.edit_type,
            stats=stats,
            diff=file_patch.patch or "",
        )

    def _generate_diff_content(self, repository, pull_request) -> list[FilePatchInfo]:
        """Generate diff content for a pull request.

        Returns FilePatchInfo list instead of concatenated string.
        Breaking change: diff_content concatenation removed.

        Args:
            repository: GitHub repository instance
            pull_request: GitHub pull request instance

        Returns:
            list[FilePatchInfo]: File metadata and patch content,
            empty list on error
        """
        try:
            # Get the latest commit SHA for the PR
            latest_commit_sha = pull_request.head.sha
            if not latest_commit_sha:
                return []

            # Get the base commit SHA (merge base)
            base_commit_sha = self._get_base_commit_sha(repository, pull_request)
            if not base_commit_sha:
                return []

            # Get and process files
            github_files = pull_request.get_files()
            if not github_files:
                return []

            # Process files to create FilePatchInfo objects with content
            if self._file_processor:
                # Use the proper file processor if available
                diff_files = self._file_processor.process_files_to_patches(
                    list(github_files), repository, latest_commit_sha, base_commit_sha
                )
            else:
                # Fallback to simple conversion
                diff_files = self._convert_github_files_to_file_patch_info(github_files)

            return diff_files

        except PR_SERVICE_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error("Failed to generate diff content", extra=sanitized)
            return []

    def _get_base_commit_sha(self, repository, pull_request) -> Optional[str]:
        """Get the base commit SHA for the pull request.

        Args:
            repository: GitHub repository instance
            pull_request: GitHub pull request instance

        Returns:
            Optional[str]: Base commit SHA, None on error
        """
        try:
            # Try to get the merge base
            base_branch: Optional[str] = pull_request.base.sha
            if base_branch:
                return base_branch

            # Fallback: use the base branch reference
            base_ref = repository.get_git_ref(f"heads/{pull_request.base.ref}")
            if base_ref:
                base_sha: Optional[str] = base_ref.object.sha
                return base_sha

            return None
        except PR_SERVICE_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error("Failed to get base commit SHA", extra=sanitized)
            return None

    def validate_repository_access(
        self,
        repo_owner: str,
        repo_name: str,
    ) -> bool:
        """Validate that the repository exists and is accessible.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name

        Returns:
            bool: True if repository is accessible, False otherwise
        """
        try:
            repository = self._github_api.get_repository(f"{repo_owner}/{repo_name}")
            return repository is not None
        except PR_SERVICE_EXCEPTIONS as e:
            # Log the error and return False for graceful degradation
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(
                "Failed to validate repository access",
                repo_owner=repo_owner,
                repo_name=repo_name,
                extra=sanitized,
            )
            return False
