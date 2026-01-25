"""GitHub API client for repository and pull request operations."""

import time
from collections import OrderedDict
from typing import Optional, Dict, List, Any, cast, Tuple, Type
from github import Github, GithubException
from github.Auth import Token
from github.Repository import Repository
from github.PullRequest import PullRequest
from github.ContentFile import ContentFile
from prdiffer.domain.services import GitHubAPIServiceInterface
from prdiffer.infrastructure.utils.retry_handler import (
    get_retry_handler,
    get_advanced_retry_handler,
    OperationContext,
)
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)
from prdiffer.infrastructure.async_parallel_executor import (
    AsyncParallelExecutor,
    ErrorStrategy,
)


# Exceptions to catch in GitHub API operations
# Note: We deliberately exclude KeyboardInterrupt, SystemExit, and GeneratorExit
# to allow system-level exceptions to propagate for proper shutdown/cleanup.
GITHUB_API_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
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


# Default cache settings
DEFAULT_FILE_CONTENT_CACHE_MAX_SIZE = 1000
DEFAULT_FILE_CONTENT_CACHE_TTL = 600  # 10 minutes


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
        file_content_cache_max_size: int = DEFAULT_FILE_CONTENT_CACHE_MAX_SIZE,
        file_content_cache_ttl: int = DEFAULT_FILE_CONTENT_CACHE_TTL,
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
            file_content_cache_max_size: Maximum number of entries in file content cache
            file_content_cache_ttl: TTL for file content cache entries in seconds
        """
        self._github_client: Optional[Github] = None
        self._logger = logger or get_logger()

        # File content cache configuration (LRU with TTL)
        self._cache_max_size = file_content_cache_max_size
        self._cache_ttl = file_content_cache_ttl

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

        # LRU cache using OrderedDict: stores (content, timestamp) tuples
        self._file_content_cache: OrderedDict[tuple, Dict[str, Any]] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0
        self._cache_evictions_ttl = 0  # Track TTL-based evictions
        self._cache_evictions_size = 0  # Track size-based evictions

        # Async parallel executor for concurrent operations
        self._async_executor = AsyncParallelExecutor(
            max_concurrent=4,  # Default max concurrent operations
            error_strategy=ErrorStrategy.IGNORE,
            logger=self._logger,
        )

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

        Raises:
            RuntimeError: If GitHub client is not initialized
        """
        if not self._github_client:
            raise RuntimeError(
                "GitHub client not initialized. Call initialize_client() before using get_repository()."
            )

        try:
            result = self._retry_handler.execute_with_retry(
                self._github_client.get_repo,
                repo_full_name,
                context=OperationContext.REPOSITORY_ACCESS,
            )
            return cast(Optional[Repository], result)
        except GITHUB_API_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(
                f"Failed to get repository {repo_full_name}", extra=sanitized
            )
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
        except GITHUB_API_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(
                f"Failed to get pull request #{pr_number}", extra=sanitized
            )
            return None

    def _is_cache_entry_valid(self, cache_key: tuple) -> bool:
        """Check if a cache entry exists and is not expired.

        Args:
            cache_key: The cache key tuple (file_path, branch)

        Returns:
            bool: True if entry exists and is valid, False otherwise
        """
        if cache_key not in self._file_content_cache:
            return False

        entry = self._file_content_cache[cache_key]
        age = time.time() - float(entry["timestamp"])
        return bool(age < self._cache_ttl)

    def _evict_oldest_entries(self) -> None:
        """Evict oldest entries when cache exceeds max size (LRU eviction).

        Also proactively removes expired entries to maintain cache hygiene.
        """
        current_time = time.time()

        # First, remove any expired entries
        expired_keys = []
        for key, entry in self._file_content_cache.items():
            age = current_time - float(entry["timestamp"])
            if age >= self._cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            self._file_content_cache.pop(key)
            self._cache_evictions_ttl += 1

        if expired_keys:
            self._logger.debug(
                f"Cache eviction (TTL): removed {len(expired_keys)} expired entries "
                f"[size={len(self._file_content_cache)}/{self._cache_max_size}]"
            )

        # Then, remove oldest entries if still over size limit
        while len(self._file_content_cache) >= self._cache_max_size:
            # OrderedDict.popitem(last=False) removes oldest entry
            evicted_key, _ = self._file_content_cache.popitem(last=False)
            self._cache_evictions_size += 1
            self._cache_evictions += 1
            self._logger.debug(
                f"Cache eviction (LRU): {evicted_key[0][:50]}... "
                f"[size={len(self._file_content_cache)}/{self._cache_max_size}]"
            )

    def _cache_set(self, cache_key: tuple, content: str) -> None:
        """Add or update a cache entry with LRU eviction.

        Args:
            cache_key: The cache key tuple (file_path, branch)
            content: The file content to cache
        """
        # If key exists, remove it first to update its position (move to end)
        if cache_key in self._file_content_cache:
            del self._file_content_cache[cache_key]
        else:
            # New entry - check if we need to evict
            self._evict_oldest_entries()

        # Add entry at the end (most recently used)
        self._file_content_cache[cache_key] = {
            "content": content,
            "timestamp": time.time(),
        }

    def _cache_get(self, cache_key: tuple) -> Optional[str]:
        """Get a cache entry, updating its LRU position if valid.

        Args:
            cache_key: The cache key tuple (file_path, branch)

        Returns:
            Optional[str]: Cached content if valid, None otherwise
        """
        if not self._is_cache_entry_valid(cache_key):
            if cache_key in self._file_content_cache:
                # Entry expired, remove it
                del self._file_content_cache[cache_key]
            self._cache_misses += 1
            return None

        # Move to end (mark as recently used)
        self._file_content_cache.move_to_end(cache_key)
        self._cache_hits += 1
        return str(self._file_content_cache[cache_key]["content"])

    def get_file_content(
        self, repository: Repository, file_path: str, branch: str
    ) -> str:
        """Get file content from a specific branch with LRU caching and TTL.

        Args:
            repository: GitHub repository instance
            file_path: Path to the file in the repository
            branch: Branch or commit SHA

        Returns:
            str: File content as string, empty string on error
        """
        # Check cache first (with TTL validation)
        cache_key = (file_path, branch)
        cached_content = self._cache_get(cache_key)
        if cached_content is not None:
            return cached_content

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

            # Cache the result with LRU eviction
            self._cache_set(cache_key, file_content)
            return file_content

        except GITHUB_API_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.warning(
                f"Failed to get content for file '{file_path}' in branch '{branch}'",
                extra=sanitized,
            )
            file_content = ""
            # Cache even failures to avoid repeated API calls
            self._cache_set(cache_key, file_content)
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
        results: Dict[str, str] = {}
        files_to_fetch = []

        # Check cache first for each file (with TTL validation)
        for file_path in file_paths:
            cache_key = (file_path, branch)
            cached_content = self._cache_get(cache_key)
            if cached_content is not None:
                results[file_path] = cached_content
            else:
                files_to_fetch.append(file_path)

        # Process remaining files
        for file_path in files_to_fetch:
            content = self.get_file_content(repository, file_path, branch)
            results[file_path] = content

        return results

    async def _get_file_content_async(
        self, repository: Repository, file_path: str, branch: str
    ) -> str:
        """Async version of get_file_content for parallel processing.

        Args:
            repository: GitHub repository instance
            file_path: Path to the file in the repository
            branch: Branch or commit SHA

        Returns:
            str: File content as string, empty string on error
        """
        # Check cache first (with TTL validation)
        cache_key = (file_path, branch)
        cached_content = self._cache_get(cache_key)
        if cached_content is not None:
            return cached_content

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

            # Cache the result with LRU eviction
            self._cache_set(cache_key, file_content)
            return file_content

        except GITHUB_API_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.warning(
                f"Failed to get content for file '{file_path}' in branch '{branch}'",
                extra=sanitized,
            )
            file_content = ""
            # Cache even failures to avoid repeated API calls
            self._cache_set(cache_key, file_content)
            return file_content

    async def _get_files_content_batch_parallel_async(
        self,
        repository: Repository,
        file_paths: List[str],
        branch: str,
        max_workers: int = 4,
    ) -> Dict[str, str]:
        """Async version of parallel batch file content retrieval.

        Uses AsyncParallelExecutor for concurrent file fetching.

        Args:
            repository: GitHub repository instance
            file_paths: List of file paths to retrieve
            branch: Branch or commit SHA
            max_workers: Maximum number of concurrent workers (default: 4)

        Returns:
            Dict mapping file paths to their content (empty string on error)
        """
        results: Dict[str, str] = {}
        files_to_fetch = []

        # Check cache first for each file (with TTL validation)
        for file_path in file_paths:
            cache_key = (file_path, branch)
            cached_content = self._cache_get(cache_key)
            if cached_content is not None:
                results[file_path] = cached_content
            else:
                files_to_fetch.append(file_path)

        if not files_to_fetch:
            return results

        # Fetch remaining files in parallel using async executor
        start_time = time.time()
        fetched_contents = await self._async_executor.execute_batch(
            lambda fp: self._get_file_content_async(repository, fp, branch),
            files_to_fetch,
        )

        # Process results
        for file_path, content in zip(files_to_fetch, fetched_contents):
            results[file_path] = content

        elapsed = time.time() - start_time
        self._logger.debug(
            f"Async parallel batch fetch: {len(files_to_fetch)} files in {elapsed:.2f}s "
            f"({elapsed / len(files_to_fetch) * 1000:.1f}ms/file avg)"
        )

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
