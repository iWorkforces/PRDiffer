"""GitHub API client for repository and pull request operations."""

from typing import Optional, Dict, List, cast
from github import Github
from github.Auth import Token
from github.Repository import Repository
from github.PullRequest import PullRequest
from github.ContentFile import ContentFile
from ccpragents.domain.services import GitHubAPIServiceInterface
from ccpragents.infrastructure.utils.retry_handler import (
    get_retry_handler,
    get_advanced_retry_handler,
    OperationContext,
)
from ccpragents.infrastructure.logging.console_logger import get_logger


class GitHubAPIClient(GitHubAPIServiceInterface):
    """GitHub API client implementation for repository operations.

    This class provides GitHub API interactions with proper error handling,
    retry logic, and caching for repository and pull request operations.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30,
        retry_on_404: bool = False,
        retry_on_403: bool = True,
        retry_on_500: bool = True,
        retry_log_level: str = "DEBUG",
        permanent_failure_log_level: str = "INFO",
        circuit_breaker_enabled: bool = True,
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_timeout: float = 60.0,
        adaptive_retry_enabled: bool = True,
        max_adaptive_delay: float = 30.0,
        api_health_tracking: bool = True,
        context_aware_retry: bool = True,
        use_advanced_retry: bool = True,
        logger=None,
    ):
        """Initialize the GitHub API client.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            timeout: API timeout in seconds
            retry_on_404: Whether to retry 404 (Not Found) errors
            retry_on_403: Whether to retry 403 (Forbidden) errors
            retry_on_500: Whether to retry 5xx server errors
            retry_log_level: Log level for retry attempts
            permanent_failure_log_level: Log level for permanent failures
            circuit_breaker_enabled: Enable circuit breaker pattern
            circuit_breaker_failure_threshold: Failures before opening circuit
            circuit_breaker_timeout: Seconds to keep circuit open
            adaptive_retry_enabled: Enable adaptive retry delays
            max_adaptive_delay: Maximum adaptive delay in seconds
            api_health_tracking: Enable API health tracking
            context_aware_retry: Enable context-aware retry strategies
            use_advanced_retry: Use advanced retry handler (Phase 3)
            logger: Logger instance for logging operations
        """
        self._github_client: Optional[Github] = None
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._timeout = timeout
        self._logger = logger or get_logger()

        # Choose retry handler based on configuration
        if use_advanced_retry:
            self._retry_handler = get_advanced_retry_handler(
                max_retries=max_retries,
                retry_delay=retry_delay,
                retry_on_404=retry_on_404,
                retry_on_403=retry_on_403,
                retry_on_500=retry_on_500,
                retry_log_level=retry_log_level,
                permanent_failure_log_level=permanent_failure_log_level,
                circuit_breaker_enabled=circuit_breaker_enabled,
                circuit_breaker_failure_threshold=circuit_breaker_failure_threshold,
                circuit_breaker_timeout=circuit_breaker_timeout,
                adaptive_retry_enabled=adaptive_retry_enabled,
                max_adaptive_delay=max_adaptive_delay,
                api_health_tracking=api_health_tracking,
                context_aware_retry=context_aware_retry,
                logger=self._logger,
            )
        else:
            self._retry_handler = get_retry_handler(
                max_retries=max_retries,
                retry_delay=retry_delay,
                retry_on_404=retry_on_404,
                retry_on_403=retry_on_403,
                retry_on_500=retry_on_500,
                retry_log_level=retry_log_level,
                permanent_failure_log_level=permanent_failure_log_level,
            )
        self._file_content_cache: Dict[tuple, str] = {}

    def initialize_client(
        self, github_token: Optional[str] = None, timeout: int = 30
    ) -> None:
        """Initialize the GitHub client with authentication.

        Args:
            github_token: GitHub personal access token for authentication
            timeout: API timeout in seconds
        """
        if github_token:
            auth = Token(github_token)
            self._github_client = Github(auth=auth, timeout=timeout)
        else:
            self._github_client = Github(timeout=timeout)

    def get_repository(self, repo_full_name: str) -> Optional[Repository]:
        """Get a GitHub repository instance with retry logic.

        Args:
            repo_full_name: Repository full name in format "owner/repo"

        Returns:
            Repository instance if found, None otherwise
        """
        if not self._github_client:
            self._logger.error("GitHub client not initialized")
            return None

        try:
            result = self._retry_handler.execute_with_retry(
                self._github_client.get_repo,
                repo_full_name,
                context=OperationContext.REPOSITORY_ACCESS,
            )
            return cast(Optional[Repository], result)
        except Exception as e:
            self._logger.error(f"Failed to get repository {repo_full_name}: {e}")
            return None

    def get_pull_request(
        self, repository: Repository, pr_number: int
    ) -> Optional[PullRequest]:
        """Get a pull request instance with retry logic.

        Args:
            repository: GitHub repository instance
            pr_number: Pull request number

        Returns:
            PullRequest instance if found, None otherwise
        """
        try:
            result = self._retry_handler.execute_with_retry(
                repository.get_pull, pr_number, context=OperationContext.PULL_REQUEST
            )
            return cast(Optional[PullRequest], result)
        except Exception as e:
            self._logger.error(f"Failed to get pull request #{pr_number}: {e}")
            return None

    def get_file_content(
        self, repository: Repository, file_path: str, branch: str
    ) -> str:
        """Get file content from a specific branch with caching.

        Args:
            repository: GitHub repository instance
            file_path: Path to the file in the repository
            branch: Branch or commit SHA

        Returns:
            str: File content as string, empty string on error
        """
        # Check cache first
        cache_key = (file_path, branch)
        if cache_key in self._file_content_cache:
            return self._file_content_cache[cache_key]

        try:
            content = self._retry_handler.execute_with_retry(
                repository.get_contents,
                file_path,
                ref=branch,
                context=OperationContext.FILE_CONTENT,
            )

            # get_contents can return either ContentFile or list[ContentFile]
            if isinstance(content, list):
                # Directory instead of file
                self._logger.warning(
                    f"Expected single file but got directory for path '{file_path}' "
                    f"in branch '{branch}'. Found {len(content)} items."
                )
                file_content = ""
            else:
                # Single file content
                file_content = self._extract_file_content(content)

            # Cache the result
            self._file_content_cache[cache_key] = file_content
            return file_content

        except Exception as e:
            self._logger.warning(
                f"Failed to get content for file '{file_path}' in branch '{branch}': {e}"
            )
            file_content = ""
            # Cache even failures to avoid repeated API calls
            self._file_content_cache[cache_key] = file_content
            return file_content

    def get_files_content_batch(
        self, repository: Repository, file_paths: List[str], branch: str
    ) -> Dict[str, str]:
        """Batch retrieve file contents from a specific branch.

        Args:
            repository: GitHub repository instance
            file_paths: List of file paths to retrieve
            branch: Branch or commit SHA

        Returns:
            Dict mapping file paths to their content (empty string on error)
        """
        results = {}
        files_to_fetch = []

        # Check cache first for each file
        for file_path in file_paths:
            cache_key = (file_path, branch)
            if cache_key in self._file_content_cache:
                results[file_path] = self._file_content_cache[cache_key]
            else:
                files_to_fetch.append(file_path)

        # Process remaining files
        for file_path in files_to_fetch:
            content = self.get_file_content(repository, file_path, branch)
            results[file_path] = content

        return results

    def _extract_file_content(self, content: ContentFile) -> str:
        """Extract file content from ContentFile object.

        Args:
            content: ContentFile object from GitHub API

        Returns:
            str: Decoded file content, empty string if unavailable
        """
        if content and hasattr(content, "decoded_content") and content.decoded_content:
            return str(content.decoded_content.decode())
        return ""

    def clear_cache(self):
        """Clear the file content cache."""
        self._file_content_cache.clear()

    def get_cache_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dict containing cache statistics
        """
        return {
            "cache_size": len(self._file_content_cache),
            "cache_keys": list(self._file_content_cache.keys()),
        }


def get_github_api_client(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: int = 30,
    retry_on_404: bool = False,
    retry_on_403: bool = True,
    retry_on_500: bool = True,
    retry_log_level: str = "DEBUG",
    permanent_failure_log_level: str = "INFO",
    # Phase 3 parameters
    circuit_breaker_enabled: bool = True,
    circuit_breaker_failure_threshold: int = 5,
    circuit_breaker_timeout: float = 60.0,
    adaptive_retry_enabled: bool = True,
    max_adaptive_delay: float = 30.0,
    api_health_tracking: bool = True,
    context_aware_retry: bool = True,
    use_advanced_retry: bool = True,
) -> GitHubAPIClient:
    """Get a configured GitHub API client instance.

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds
        timeout: API timeout in seconds
        retry_on_404: Whether to retry 404 (Not Found) errors
        retry_on_403: Whether to retry 403 (Forbidden) errors
        retry_on_500: Whether to retry 5xx server errors
        retry_log_level: Log level for retry attempts
        permanent_failure_log_level: Log level for permanent failures
        circuit_breaker_enabled: Enable circuit breaker pattern
        circuit_breaker_failure_threshold: Failures before opening circuit
        circuit_breaker_timeout: Seconds to keep circuit open
        adaptive_retry_enabled: Enable adaptive retry delays
        max_adaptive_delay: Maximum adaptive delay in seconds
        api_health_tracking: Enable API health tracking
        context_aware_retry: Enable context-aware retry strategies
        use_advanced_retry: Use advanced retry handler (Phase 3)

        Returns:
            GitHubAPIClient: Configured GitHub API client instance
    """
    return GitHubAPIClient(
        max_retries=max_retries,
        retry_delay=retry_delay,
        timeout=timeout,
        retry_on_404=retry_on_404,
        retry_on_403=retry_on_403,
        retry_on_500=retry_on_500,
        retry_log_level=retry_log_level,
        permanent_failure_log_level=permanent_failure_log_level,
        circuit_breaker_enabled=circuit_breaker_enabled,
        circuit_breaker_failure_threshold=circuit_breaker_failure_threshold,
        circuit_breaker_timeout=circuit_breaker_timeout,
        adaptive_retry_enabled=adaptive_retry_enabled,
        max_adaptive_delay=max_adaptive_delay,
        api_health_tracking=api_health_tracking,
        context_aware_retry=context_aware_retry,
        use_advanced_retry=use_advanced_retry,
    )
