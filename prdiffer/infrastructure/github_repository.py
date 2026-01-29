"""GitHub repository implementation for PR diff data retrieval (Refactored).

This is the refactored version using composition with extracted components.
"""

import os
from typing import Optional, Dict
from github.Repository import Repository
from github.PullRequest import PullRequest
from github.GithubException import (
    GithubException,
    UnknownObjectException,
    RateLimitExceededException,
)
import asyncer
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.file_diff_response import FileDiffResponse
from prdiffer.domain.repositories import PRDiffRepositoryInterface
from prdiffer.domain.services.logger import LoggerServiceInterface, LogLevel
from prdiffer.infrastructure.settings import SettingsService, get_settings_service
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)
from prdiffer.infrastructure.security.input_validator import InputValidator

from prdiffer.infrastructure.github.api_client import get_github_api_client
from prdiffer.infrastructure.github.file_processor import get_file_processor
from prdiffer.infrastructure.github.diff_generator import get_diff_generator
from prdiffer.infrastructure.utils.pattern_matcher import get_pattern_matcher
from prdiffer.infrastructure.utils.diff_utils import get_diff_utils
from prdiffer.infrastructure.services.pr_diff_service import GitHubPRDiffService


class GitHubPRDiffRepository(PRDiffRepositoryInterface):
    """GitHub repository implementation for PR diff data retrieval.

    This refactored class uses composition with extracted components for
    better separation of concerns and maintainability.

    Attributes:
        repo_owner: Repository owner/organization name
        repo_name: Repository name
        pr_number: Pull request number
    """

    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        github_token: Optional[str] = None,
        settings_service: Optional[SettingsService] = None,
        logger: Optional[LoggerServiceInterface] = None,
        input_validator: Optional[InputValidator] = None,
    ):
        """Initialize GitHub repository with repository details and optional authentication.

        Args:
            repo_owner: The owner/organization of repository
            repo_name: The name of repository
            pr_number: The pull request number
            github_token: GitHub personal access token. If not provided,
                         uses GITHUB_TOKEN environment variable or anonymous access.
            settings_service: Optional settings service for DI
            logger: Optional logger service for DI
            input_validator: Optional input validator for DI
        """
        self._repo_owner = repo_owner
        self._repo_name = repo_name
        self._pr_number = pr_number

        self.settings_service: SettingsService = (
            settings_service or get_settings_service()
        )
        self._logger = logger or get_logger()
        self._input_validator = input_validator or InputValidator()

        github_settings = self.settings_service.get_github_settings()
        app_settings = self.settings_service.get_app_settings()

        # Get GitHub token from parameter or environment variable
        # Priority: parameter > GITHUB_TOKEN environment variable
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")

        # Get configuration values
        self.rate_limit = github_settings.get("rate_limit", 5000)
        self.timeout = github_settings.get("timeout", 30)
        self.max_retries = github_settings.get("max_retries", 3)
        self.retry_delay = github_settings.get("retry_delay", 1)
        self.ignore_patterns = github_settings.get("ignore_patterns", [])
        self.valid_extensions = github_settings.get("valid_extensions", [])
        self.max_files_allowed = app_settings.get("max_files_allowed", 50)

        # Get smart retry configuration (Phase 2)
        self.retry_on_404 = github_settings.get("retry_on_404", False)
        self.retry_on_403 = github_settings.get("retry_on_403", True)
        self.retry_on_500 = github_settings.get("retry_on_500", True)
        self.retry_log_level = github_settings.get("retry_log_level", "DEBUG")
        self.permanent_failure_log_level = github_settings.get(
            "permanent_failure_log_level", "INFO"
        )

        # Get Phase 3 advanced retry configuration
        self.circuit_breaker_enabled = github_settings.get(
            "circuit_breaker_enabled", True
        )
        self.circuit_breaker_failure_threshold = github_settings.get(
            "circuit_breaker_failure_threshold", 5
        )
        self.circuit_breaker_timeout = github_settings.get(
            "circuit_breaker_timeout", 60.0
        )
        self.adaptive_retry_enabled = github_settings.get(
            "adaptive_retry_enabled", True
        )
        self.max_adaptive_delay = github_settings.get("max_adaptive_delay", 30.0)
        self.api_health_tracking = github_settings.get("api_health_tracking", True)
        self.context_aware_retry = github_settings.get("context_aware_retry", True)
        self.use_advanced_retry = github_settings.get("use_advanced_retry", True)

        # Get diff parallel processing configuration
        self.diff_parallel_enabled = github_settings.get("diff_parallel_enabled", True)
        self.diff_parallel_threshold = github_settings.get("diff_parallel_threshold", 3)
        self.diff_max_workers = github_settings.get("diff_max_workers", 4)
        self.diff_worker_timeout = github_settings.get("diff_worker_timeout", 30.0)

        # File processing parallel fetch configuration
        self.file_parallel_threshold = self.settings_service.get(
            "file_processing.parallel_fetch_threshold", 10
        )
        self.file_parallel_workers = self.settings_service.get(
            "file_processing.concurrent_downloads", 3
        )

        # Diff truncation configuration
        self._diff_truncate_enabled = self.settings_service.get(
            "diff.truncate_enabled", False
        )
        self._diff_max_total_chars = int(
            self.settings_service.get("diff.max_total_chars", 200000)
        )
        self._diff_truncation_notice = self.settings_service.get(
            "diff.truncation_notice", "[DIFF TRUNCATED]"
        )

        # Initialize composed components
        self._github_api_client = get_github_api_client(
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            timeout=self.timeout,
            retry_on_404=self.retry_on_404,
            retry_on_403=self.retry_on_403,
            retry_on_500=self.retry_on_500,
            retry_log_level=self.retry_log_level,
            permanent_failure_log_level=self.permanent_failure_log_level,
            # Phase 3 parameters
            circuit_breaker_enabled=self.circuit_breaker_enabled,
            circuit_breaker_failure_threshold=self.circuit_breaker_failure_threshold,
            circuit_breaker_timeout=self.circuit_breaker_timeout,
            adaptive_retry_enabled=self.adaptive_retry_enabled,
            max_adaptive_delay=self.max_adaptive_delay,
            api_health_tracking=self.api_health_tracking,
            context_aware_retry=self.context_aware_retry,
            use_advanced_retry=self.use_advanced_retry,
        )

        self._pattern_matcher = get_pattern_matcher(
            ignore_patterns=self.ignore_patterns, valid_extensions=self.valid_extensions
        )

        self._diff_utils = get_diff_utils()

        self._file_processor = get_file_processor(
            github_api_service=self._github_api_client,
            pattern_matcher=self._pattern_matcher,
            diff_utils=self._diff_utils,
            max_files_allowed=self.max_files_allowed,
            parallel_fetch_threshold=self.file_parallel_threshold,
            max_parallel_workers=self.file_parallel_workers,
        )

        # Note: Parallel executor disabled for simplicity.
        # The async migration has moved parallel processing to FileProcessor and APIClient
        # which use AsyncParallelExecutor internally.
        # DiffGenerator will use sequential processing.
        self._parallel_executor = None

        self._diff_generator = get_diff_generator(
            diff_utils=self._diff_utils,
            parallel_executor=self._parallel_executor,
            parallel_enabled=self.diff_parallel_enabled,
            parallel_threshold=self.diff_parallel_threshold,
        )

        # Lazy initialization for GitHub objects
        self._repository: Optional[Repository] = None
        self._pull_request: Optional[PullRequest] = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Initialize the repository connection.

        This method sets up the GitHub client and validates repository access.

        Raises:
            RuntimeError: If the repository is not accessible
        """
        self._initialize_github_objects()
        if not self._initialized:
            raise RuntimeError(
                f"Failed to initialize repository {self._repo_owner}/{self._repo_name}"
            )

    @property
    def repo_owner(self) -> str:
        """Repository owner/organization name."""
        return self._repo_owner

    @property
    def repo_name(self) -> str:
        """Repository name."""
        return self._repo_name

    @property
    def pr_number(self) -> int:
        """Pull request number."""
        return self._pr_number

    def _initialize_github_objects(self):
        """Lazy initialization of GitHub client, repository, and PR objects."""
        if self._initialized:
            return

        # Initialize GitHub API client
        self._github_api_client.initialize_client(
            github_token=self.github_token, timeout=self.timeout
        )

        # Define repository full name for error messages
        repo_full_name = f"{self._repo_owner}/{self._repo_name}"

        try:
            self._repository = self._github_api_client.get_repository(repo_full_name)
        except (UnknownObjectException, RateLimitExceededException) as e:
            sanitized = sanitize_exception_for_logging(e)
            self._logger.warning(
                f"Repository not accessible: {repo_full_name}", extra=sanitized
            )
            # Re-raise immediately to preserve exception context
            raise RuntimeError(
                f"Failed to initialize repository {repo_full_name} - repository may not exist or access may be denied"
            ) from e
        except GithubException as e:
            sanitized = sanitize_exception_for_logging(e)
            self._logger.error(
                f"GitHub API error accessing repository {repo_full_name}",
                extra=sanitized,
            )
            # Re-raise immediately to preserve exception context
            raise RuntimeError(
                f"GitHub API error accessing repository {repo_full_name}"
            ) from e

        try:
            if self._repository is None:
                raise RuntimeError(f"Repository {repo_full_name} is not initialized")
            self._pull_request = self._github_api_client.get_pull_request(
                self._repository, self._pr_number
            )
        except (UnknownObjectException, RateLimitExceededException) as e:
            sanitized = sanitize_exception_for_logging(e)
            self._logger.warning(
                f"Pull request #{self._pr_number} not accessible in {repo_full_name}",
                extra=sanitized,
            )
            # Re-raise immediately to preserve exception context
            raise RuntimeError(
                f"Failed to initialize pull request #{self._pr_number} for repository {repo_full_name} - pull request may not exist or be inaccessible"
            ) from e
        except GithubException as e:
            sanitized = sanitize_exception_for_logging(e)
            self._logger.error(
                f"GitHub API error fetching pull request #{self._pr_number}",
                extra=sanitized,
            )
            # Re-raise immediately to preserve exception context
            raise RuntimeError(
                f"GitHub API error fetching pull request #{self._pr_number}"
            ) from e

        self._initialized = True

    async def get_latest_commit_sha(self) -> str:
        """Get the latest head commit SHA for the pull request.

        Returns:
            str: The latest head commit SHA

        Raises:
            RuntimeError: If GitHub objects failed to initialize
            ValueError: If pull request cannot be refreshed
        """
        return await asyncer.asyncify(self._get_latest_commit_sha_sync)()

    async def get_pr_diff(self) -> PRDiff:
        """Fetch PR diff information from GitHub.

        Returns:
            PRDiff: A PRDiff object containing complete PR information including:
                - PR number, repository details
                - Diff content with full file context
                - Base and head commit SHAs
                - File change statistics (changed files, additions, deletions)
                - Commit messages

        Raises:
            RuntimeError: If GitHub objects failed to initialize
        """
        return await asyncer.asyncify(self._get_pr_diff_sync)()

    async def approve_pr_with_comment(self, pr_url: str, compliment: str) -> str:
        """Approve a GitHub PR with a compliment comment.

        This method:
        1. Parses the PR URL to extract owner, repo, and PR number
        2. Validates PR exists and is accessible
        3. Calls pr.create_review() with event="APPROVE" and the compliment as body
        4. Returns success message or raises exceptions loudly on failures

        Args:
            pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            compliment: The compliment text to include in the approval review

        Returns:
            str: Success message indicating PR was approved

        Raises:
            InvalidURLError: If PR URL format is invalid
            RuntimeError: If GitHub objects failed to initialize
            GithubException: If PR approval fails (404, 403, rate limit, etc.)
        """
        # Validate inputs
        if not compliment:
            raise ValueError("Compliment cannot be empty")

        if not isinstance(compliment, str):
            raise ValueError(
                f"Compliment must be a string, got {type(compliment).__name__}"
            )

        # Sanitize compliment for logging
        safe_compliment = self._input_validator.sanitize_for_logging(
            compliment, max_length=500
        )

        # Parse PR URL to get components
        repo_owner, repo_name, pr_number = self._input_validator.validate_github_url(
            pr_url
        )

        # Check if parsed components match current instance
        if repo_owner != self._repo_owner or repo_name != self._repo_name:
            self._logger.warning(
                f"PR URL components do not match repository instance: "
                f"expected {self._repo_owner}/{self._repo_name}, got {repo_owner}/{repo_name}",
                pr_url=pr_url[:100],
            )

        if pr_number != self._pr_number:
            self._logger.warning(
                f"PR number does not match repository instance: "
                f"expected {self._pr_number}, got {pr_number}",
                pr_url=pr_url[:100],
            )

        self._logger.info(
            f"Approving PR #{pr_number} in {repo_owner}/{repo_name}",
            pr_number=pr_number,
            repo=repo_name,
            owner=repo_owner,
            compliment=safe_compliment,
        )

        # Initialize GitHub objects if not already initialized
        self._initialize_github_objects()

        # Verify PR exists and is accessible
        if self._pull_request is None:
            raise RuntimeError(
                f"Failed to access pull request #{pr_number} "
                f"in repository {repo_owner}/{repo_name} - "
                "pull request may not exist or be inaccessible"
            )

        try:
            # Call create_review() with APPROVE event and compliment as body
            # This single call both approves the PR and posts the comment
            review = self._pull_request.create_review(
                event="APPROVE",
                body=compliment,
            )

            self._logger.info(
                f"Successfully approved PR #{pr_number}",
                pr_number=pr_number,
                review_id=review.id if hasattr(review, "id") else "unknown",
            )

            return f"Successfully approved PR #{pr_number} in {repo_owner}/{repo_name}"

        except GithubException as e:
            sanitized = sanitize_exception_for_logging(e)

            if "404" in str(e).lower() or "not found" in str(e).lower():
                self._logger.error(
                    f"Pull request #{pr_number} not found in {repo_owner}/{repo_name}",
                    extra=sanitized,
                    pr_number=pr_number,
                )
                raise RuntimeError(
                    f"Pull request #{pr_number} not found in repository {repo_owner}/{repo_name}"
                ) from e

            if "403" in str(e).lower() or "forbidden" in str(e).lower():
                self._logger.error(
                    f"Permission denied for PR #{pr_number} - insufficient permissions",
                    extra=sanitized,
                    pr_number=pr_number,
                )
                raise RuntimeError(
                    f"Insufficient permissions to approve PR #{pr_number} - "
                    "ensure token has 'repo' scope and write access"
                ) from e

            if "429" in str(e).lower() or "rate limit" in str(e).lower():
                self._logger.warning(
                    f"GitHub API rate limit exceeded while approving PR #{pr_number}",
                    extra=sanitized,
                    pr_number=pr_number,
                )
                raise RuntimeError(
                    "GitHub API rate limit exceeded - please retry later"
                ) from e

            self._logger.error(
                f"GitHub API error while approving PR #{pr_number}",
                extra=sanitized,
                pr_number=pr_number,
            )
            raise RuntimeError(
                f"GitHub API error while approving PR #{pr_number}"
            ) from e

            if "403" in str(e).lower() or "forbidden" in str(e).lower():
                self._logger.error(
                    f"Permission denied for PR #{pr_number} - insufficient permissions",
                    extra=sanitized,
                    pr_number=pr_number,
                )
                raise RuntimeError(
                    f"Insufficient permissions to approve PR #{pr_number} - "
                    "ensure token has 'repo' scope and write access"
                ) from e

            if "429" in str(e).lower() or "rate limit" in str(e).lower():
                self._logger.warning(
                    f"GitHub API rate limit exceeded while approving PR #{pr_number}",
                    extra=sanitized,
                    pr_number=pr_number,
                )
                raise RuntimeError(
                    "GitHub API rate limit exceeded - please retry later"
                ) from e

            # Generic GitHub API error
            self._logger.error(
                f"GitHub API error while approving PR #{pr_number}",
                extra=sanitized,
                pr_number=pr_number,
            )
            raise RuntimeError(
                f"GitHub API error while approving PR #{pr_number}"
            ) from e

    def _get_latest_commit_sha_sync(self) -> str:
        self._initialize_github_objects()

        if self._repository is None:
            raise RuntimeError(
                f"Failed to initialize repository {self._repo_owner}/{self._repo_name} "
                "- GitHub objects may not have been properly initialized"
            )
        if self._pull_request is None:
            raise RuntimeError(
                f"Failed to initialize pull request #{self._pr_number} "
                "- GitHub objects may not have been properly initialized"
            )

        self._pull_request = self._github_api_client.get_pull_request(
            self._repository, self._pr_number
        )

        if self._pull_request is None:
            raise ValueError(
                f"Failed to refresh pull request #{self._pr_number} - it may have been deleted or become inaccessible"
            )

        return self._pull_request.head.sha

    def _get_pr_diff_sync(self) -> PRDiff:
        self._initialize_github_objects()

        if self._repository is None:
            raise RuntimeError(
                f"Failed to initialize repository {self._repo_owner}/{self._repo_name} "
                "- GitHub objects may not have been properly initialized"
            )
        if self._pull_request is None:
            raise RuntimeError(
                f"Failed to initialize pull request #{self._pr_number} "
                "- GitHub objects may not have been properly initialized"
            )

        base_sha, head_sha = self._get_merge_base_commits()

        pr_files = self._file_processor.get_pr_files(self._pull_request)
        filtered_files = self._file_processor.filter_files(pr_files)

        if pr_files != filtered_files:
            self._log_filtered_files(pr_files, filtered_files)

        if self._repository is None:
            raise RuntimeError(
                f"Repository {self._repo_owner}/{self._repo_name} became invalid during processing"
            )
        diff_files = self._file_processor.process_files_to_patches(
            filtered_files, self._repository, head_sha, base_sha
        )

        service = GitHubPRDiffService(
            github_api_client=self._github_api_client,
            diff_generator=self._diff_generator,
            file_processor=self._file_processor,
            logger=self._logger,
        )
        # Convert FilePatchInfo list to FileDiffResponse list
        file_responses: list[FileDiffResponse] = [
            service._convert_file_patch_info_to_response(file_patch)
            for file_patch in diff_files
        ]

        self._logger.info(f"Generated diff content for {len(file_responses)} files")

        if self._logger.should_log(LogLevel.DEBUG):
            safe_diff_preview = self._input_validator.sanitize_for_logging(
                f"Files: {len(file_responses)}",
                max_length=1000,
            )
            self._logger.debug(f"Diff content preview:\n{safe_diff_preview}")

        return PRDiff(files=file_responses)

    def _get_merge_base_commits(self) -> tuple[str, str]:
        """Get base and head commit SHAs, using merge base for accurate comparison.

        Returns:
            tuple: (base_sha, head_sha) where base_sha is the merge base commit

        Raises:
            RuntimeError: If GitHub objects are not properly initialized
        """
        # Check that objects are initialized (replace assertion with proper exception)
        if self._repository is None:
            raise RuntimeError(
                f"Repository {self._repo_owner}/{self._repo_name} not initialized"
            )
        if self._pull_request is None:
            raise RuntimeError(f"Pull request #{self._pr_number} not initialized")

        try:
            compare = self._repository.compare(
                self._pull_request.base.sha, self._pull_request.head.sha
            )
            merge_base_commit = compare.merge_base_commit
            base_sha = merge_base_commit.sha
        except (UnknownObjectException, RateLimitExceededException) as e:
            sanitized = sanitize_exception_for_logging(e)
            self._logger.warning(
                "Could not determine merge base, falling back to base commit",
                extra=sanitized,
            )
            base_sha = self._pull_request.base.sha
        except GithubException as e:
            sanitized = sanitize_exception_for_logging(e)
            self._logger.error("Failed to get merge base commit", extra=sanitized)
            base_sha = self._pull_request.base.sha

        # Check pull request again after exception handling
        if self._pull_request is None:
            raise RuntimeError(
                f"Pull request #{self._pr_number} became invalid during merge base calculation"
            )

        if base_sha != self._pull_request.base.sha:
            self._logger.info(
                f"Using merge base commit {base_sha} instead of base commit {self._pull_request.base.sha}"
            )

        head_sha = self._pull_request.head.sha
        return base_sha, head_sha

    def _sanitize_filename_for_logging(self, filename: str) -> str:
        """Sanitize a filename for safe logging.

        This prevents log injection attacks through malicious file names.

        Args:
            filename: The filename to sanitize

        Returns:
            str: A sanitized filename safe for logging
        """
        return self._input_validator.sanitize_for_logging(filename, max_length=200)

    def _log_filtered_files(self, original_files, filtered_files):
        """Log information about filtered files with sanitized names."""
        try:
            # Sanitize file names before logging to prevent log injection
            original_names = [
                self._sanitize_filename_for_logging(file.filename)
                for file in original_files
            ]
            filtered_names = [
                self._sanitize_filename_for_logging(file.filename)
                for file in filtered_files
            ]
            self._logger.info(
                "Filtered out [ignore] files for pull request:",
                extra={"files": original_names, "filtered_files": filtered_names},
            )
        except Exception as e:
            # Log warning instead of silently swallowing exceptions
            self._logger.warning(
                f"Failed to log filtered files: {e}",
                error_type=type(e).__name__,
            )


# Global instance cache for singleton pattern
_repository_cache: Dict[str, "GitHubPRDiffRepository"] = {}


def get_github_repository(
    repo_owner: str,
    repo_name: str,
    pr_number: int,
    github_token: Optional[str] = None,
    settings_service: Optional[SettingsService] = None,
    logger: Optional[LoggerServiceInterface] = None,
    input_validator: Optional[InputValidator] = None,
) -> GitHubPRDiffRepository:
    """Get a GitHub repository instance (singleton pattern per repository/PR).

    This function provides a singleton pattern for GitHubPRDiffRepository instances
    to avoid creating multiple instances for the same repository and PR.

    Args:
        repo_owner: Repository owner/organization
        repo_name: Repository name
        pr_number: Pull request number
        github_token: GitHub personal access token (optional)
        settings_service: Optional settings service for DI
        logger: Optional logger service for DI
        input_validator: Optional input validator for DI

    Returns:
        GitHubPRDiffRepository: The repository instance
    """
    global _repository_cache

    # Create a unique cache key for this repository and PR
    cache_key = f"{repo_owner}/{repo_name}/pr/{pr_number}"
    if github_token:
        cache_key = f"{cache_key}/token"

    if cache_key not in _repository_cache:
        _repository_cache[cache_key] = GitHubPRDiffRepository(
            repo_owner,
            repo_name,
            pr_number,
            github_token,
            settings_service,
            logger,
            input_validator,
        )

    return _repository_cache[cache_key]
