"""GitHub repository implementation for PR diff data retrieval (Refactored).

This is the refactored version using composition with extracted components.
"""
import os
from typing import Optional
from ccpragents.domain.entities.pr_diff import ExtraPRDiff
from ccpragents.domain.repositories import PRDiffRepositoryInterface
from ccpragents.infrastructure.settings import SettingsService, get_settings_service
from ccpragents.infrastructure.logging.console_logger import get_logger

# Import extracted components
from ccpragents.infrastructure.github.api_client import get_github_api_client
from ccpragents.infrastructure.github.file_processor import get_file_processor
from ccpragents.infrastructure.github.diff_generator import get_diff_generator
from ccpragents.infrastructure.utils.pattern_matcher import get_pattern_matcher
from ccpragents.infrastructure.utils.diff_utils import get_diff_utils


class GitHubPRDiffRepository(PRDiffRepositoryInterface):
    """GitHub repository implementation for PR diff data retrieval.

    This refactored class uses composition with extracted components for
    better separation of concerns and maintainability.

    Attributes:
        repo_owner: Repository owner/organization name
        repo_name: Repository name
        pr_number: Pull request number
    """

    def __init__(self, repo_owner: str, repo_name: str, pr_number: int, github_token: Optional[str] = None):
        """Initialize the GitHub repository with repository details and optional authentication.

        Args:
            repo_owner: The owner/organization of the repository
            repo_name: The name of the repository
            pr_number: The pull request number
            github_token: GitHub personal access token. If not provided,
                         uses GITHUB_TOKEN environment variable or anonymous access.
        """
        self._repo_owner = repo_owner
        self._repo_name = repo_name
        self._pr_number = pr_number

        # Initialize settings service
        self.settings_service: SettingsService = get_settings_service()
        github_settings = self.settings_service.get_github_settings()
        app_settings = self.settings_service.get_app_settings()

        # Get GitHub token from settings, parameter, or environment variable
        self.github_token = (
            github_token or
            github_settings.get('token') or
            os.getenv("GITHUB_TOKEN")
        )

        # Get configuration values
        self.rate_limit = github_settings.get('rate_limit', 5000)
        self.timeout = github_settings.get('timeout', 30)
        self.max_retries = github_settings.get('max_retries', 3)
        self.retry_delay = github_settings.get('retry_delay', 1)
        self.ignore_patterns = github_settings.get('ignore_patterns', [])
        self.valid_extensions = github_settings.get('valid_extensions', [])
        self.max_files_allowed = app_settings.get('max_files_allowed', 50)

        # Get smart retry configuration (Phase 2)
        self.retry_on_404 = github_settings.get('retry_on_404', False)
        self.retry_on_403 = github_settings.get('retry_on_403', True)
        self.retry_on_500 = github_settings.get('retry_on_500', True)
        self.retry_log_level = github_settings.get('retry_log_level', 'DEBUG')
        self.permanent_failure_log_level = github_settings.get('permanent_failure_log_level', 'INFO')

        # Get Phase 3 advance: d retry configuration
        self.circuit_breaker_enabled = github_settings.get('circuit_breaker_enabled', True)
        self.circuit_breaker_failure_threshold = github_settings.get('circuit_breaker_failure_threshold', 5)
        self.circuit_breaker_timeout = github_settings.get('circuit_breaker_timeout', 60.0)
        self.adaptive_retry_enabled = github_settings.get('adaptive_retry_enabled', True)
        self.max_adaptive_delay = github_settings.get('max_adaptive_delay', 30.0)
        self.api_health_tracking = github_settings.get('api_health_tracking', True)
        self.context_aware_retry = github_settings.get('context_aware_retry', True)
        self.use_advanced_retry = github_settings.get('use_advanced_retry', True)

        # Initialize logger
        self.logger = get_logger()

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
            use_advanced_retry=self.use_advanced_retry
        )

        self._pattern_matcher = get_pattern_matcher(
            ignore_patterns=self.ignore_patterns,
            valid_extensions=self.valid_extensions
        )

        self._diff_utils = get_diff_utils()

        self._file_processor = get_file_processor(
            github_api_service=self._github_api_client,
            pattern_matcher=self._pattern_matcher,
            diff_utils=self._diff_utils,
            max_files_allowed=self.max_files_allowed
        )

        self._diff_generator = get_diff_generator(
            diff_utils=self._diff_utils
        )

        # Lazy initialization for GitHub objects
        self._repository = None
        self._pull_request = None
        self._initialized = False

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
            github_token=self.github_token,
            timeout=self.timeout
        )

        # Get repository and pull request
        repo_full_name = f"{self._repo_owner}/{self._repo_name}"
        self._repository = self._github_api_client.get_repository(repo_full_name)

        if self._repository is not None:
            self._pull_request = self._github_api_client.get_pull_request(
                self._repository, self._pr_number
            )

        if self._repository is None:
            raise RuntimeError(f"Failed to initialize repository {repo_full_name}")

        if self._pull_request is None:
            raise RuntimeError(f"Failed to initialize pull request #{self._pr_number} for repository {repo_full_name}")

        self._initialized = True

    def get_latest_commit_sha(self) -> str:
        """Get the latest head commit SHA for the pull request.

        Returns:
            str: The latest head commit SHA
        """
        self._initialize_github_objects()

        # Type assertion: self._repository and self._pull_request should not be None after initialization
        assert self._repository is not None, "Repository should be initialized"
        assert self._pull_request is not None, "Pull request should be initialized"

        # Refresh the PR object to get the latest data
        self._pull_request = self._github_api_client.get_pull_request(
            self._repository, self._pr_number
        )

        if self._pull_request is None:
            raise RuntimeError(f"Failed to refresh pull request #{self._pr_number}")

        return self._pull_request.head.sha

    async def get_pr_diff(self) -> ExtraPRDiff:
        """Fetch PR diff information from GitHub.

        Returns:
            ExtraPRDiff: A ExtraPRDiff object containing complete PR information including:
                - PR number, repository details
                - Diff content with full file context
                - Base and head commit SHAs
                - File change statistics (changed files, additions, deletions)
                - Commit messages
        """
        self._initialize_github_objects()

        # Type assertion: objects should not be None after initialization
        assert self._repository is not None, "Repository should be initialized"
        assert self._pull_request is not None, "Pull request should be initialized"

        # Get merge base commit for accurate diff comparison
        base_sha, head_sha = self._get_merge_base_commits()

        # Get and process PR files
        pr_files = self._file_processor.get_pr_files(self._pull_request)
        filtered_files = self._file_processor.filter_files(pr_files)

        if pr_files != filtered_files:
            self._log_filtered_files(pr_files, filtered_files)

        # Process files to get diff information
        # Type assertion: self._repository should not be None after _initialize_github_objects()
        assert self._repository is not None, "Repository should be initialized"
        diff_files = self._file_processor.process_files_to_patches(
            filtered_files, self._repository, head_sha, base_sha
        )

        # Generate extended diff content
        extended_diffs = self._diff_generator.generate_extended_diff(
            diff_files, add_line_numbers_to_hunks=False
        )
        diff_content = "\n".join(extended_diffs)

        self.logger.info(f"Generated diff content for {len(diff_files)} files")
        self.logger.debug(f"Diff content:\n{diff_content}")

        # Get commit messages
        commit_messages = self._diff_generator.get_commit_messages(self._pull_request)

        return ExtraPRDiff(
            pr_number=self._pr_number,
            repo_owner=self._repo_owner,
            repo_name=self._repo_name,
            diff_content=diff_content,
            base_commit=self._pull_request.base.sha,
            head_commit=self._pull_request.head.sha,
            changed_files=self._pull_request.changed_files,
            additions=self._pull_request.additions,
            deletions=self._pull_request.deletions,
            commit_messages=commit_messages
        )

    def _get_merge_base_commits(self) -> tuple[str, str]:
        """Get base and head commit SHAs, using merge base for accurate comparison.

        Returns:
            tuple: (base_sha, head_sha) where base_sha is the merge base commit
        """
        try:
            # Type assertion: self._repository should not be None after _initialize_github_objects()
            assert self._repository is not None, "Repository should be initialized"
            assert self._pull_request is not None, "Pull request should be initialized"
            compare = self._repository.compare(
                self._pull_request.base.sha,
                self._pull_request.head.sha
            )
            merge_base_commit = compare.merge_base_commit
            base_sha = merge_base_commit.sha
        except Exception as e:
            self.logger.error(f"Failed to get merge base commit: {e}")
            assert self._pull_request is not None, "Pull request should be initialized"
            base_sha = self._pull_request.base.sha

        assert self._pull_request is not None, "Pull request should be initialized"
        if base_sha != self._pull_request.base.sha:
            self.logger.info(
                f"Using merge base commit {base_sha} instead of base commit {self._pull_request.base.sha}"
            )

        head_sha = self._pull_request.head.sha
        return base_sha, head_sha

    def _log_filtered_files(self, original_files, filtered_files):
        """Log information about filtered files."""
        try:
            original_names = [file.filename for file in original_files]
            filtered_names = [file.filename for file in filtered_files]
            self.logger.info(
                "Filtered out [ignore] files for pull request:",
                extra={
                    "files": original_names,
                    "filtered_files": filtered_names
                }
            )
        except Exception:
            pass
