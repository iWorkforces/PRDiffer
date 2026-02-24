"""GitHub API client implementation."""

import time
import asyncer
from collections import OrderedDict
from typing import Any, cast

from github import Github
from github.Auth import Token
from github.Repository import Repository as PyGithubRepository
from github.PullRequest import PullRequest as PyGithubPullRequest
from github.ContentFile import ContentFile

from prdiffer.domain.services import GitHubAPIServiceInterface
from prdiffer.domain.entities import Repository, PullRequest
from prdiffer.infrastructure.github.mappers import (
    map_pygithub_repository_to_domain,
    map_pygithub_pr_to_domain,
)
from prdiffer.infrastructure.utils.retry import (
    get_retry_handler,
    get_advanced_retry_handler,
    OperationContext,
)
from prdiffer.infrastructure.logging.console_logger import ConsoleLogger, get_logger
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)
from prdiffer.domain.exceptions import PRDifferException
from prdiffer.domain.errors import E5009_CONFIGURATION_ERROR
from prdiffer.infrastructure.utils.parallel import (
    AsyncParallelExecutor,
    ErrorStrategy,
)
from prdiffer.infrastructure.github.etag_adapter import ETagRequestAdapter
from prdiffer.infrastructure.github.client_models import (
    GITHUB_API_EXCEPTIONS,
    DEFAULT_FILE_CONTENT_CACHE_MAX_SIZE,
    DEFAULT_FILE_CONTENT_CACHE_TTL,
)


class GitHubAPIClient(GitHubAPIServiceInterface):
    """GitHub API client implementation for repository operations."""

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
        rate_limit_remaining_threshold: int = 1,
        rate_limit_reset_buffer: float = 1.0,
        secondary_rate_limit_backoff: float = 60.0,
        api_health_tracking: bool = True,
        context_aware_retry: bool = True,
        use_advanced_retry: bool = True,
        max_concurrent: int = 4,
        logger: "ConsoleLogger | None" = None,
        file_content_cache_max_size: int = DEFAULT_FILE_CONTENT_CACHE_MAX_SIZE,
        file_content_cache_ttl: int = DEFAULT_FILE_CONTENT_CACHE_TTL,
    ):
        self._github_client: Github | None = None
        self._logger = logger or get_logger()

        self._cache_max_size = file_content_cache_max_size
        self._cache_ttl = file_content_cache_ttl

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
                rate_limit_remaining_threshold=rate_limit_remaining_threshold,
                rate_limit_reset_buffer=rate_limit_reset_buffer,
                secondary_rate_limit_backoff=secondary_rate_limit_backoff,
                api_health_tracking=api_health_tracking,
                context_aware_retry=context_aware_retry,
                logger=None,
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
                rate_limit_remaining_threshold=rate_limit_remaining_threshold,
                rate_limit_reset_buffer=rate_limit_reset_buffer,
                secondary_rate_limit_backoff=secondary_rate_limit_backoff,
            )

        self._file_content_cache: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0
        self._cache_evictions_ttl = 0
        self._cache_evictions_size = 0

        self._async_executor = AsyncParallelExecutor(
            max_concurrent=max_concurrent,
            error_strategy=ErrorStrategy.IGNORE,
            logger=self._logger,
        )

        self._etag_request_adapter = ETagRequestAdapter(
            cache_service=None,
            enabled=True,
            etag_ttl=self._cache_ttl,
            etag_cache_size=self._cache_max_size,
            logger=self._logger,
        )

    def initialize_client(self, github_token: str | None = None, timeout: int = 30) -> None:
        if github_token:
            auth = Token(github_token)
            self._github_client = Github(auth=auth, timeout=timeout)
        else:
            self._github_client = Github(timeout=timeout)

    def get_repository(self, repo_full_name: str) -> Repository | None:
        if not self._github_client:
            raise PRDifferException(
                "GitHub client not initialized. Call initialize_client() before using get_repository().",
                error_code=E5009_CONFIGURATION_ERROR,
            )

        try:
            pygithub_repo = self._retry_handler.execute_with_retry(
                self._github_client.get_repo,
                repo_full_name,
                context=OperationContext.REPOSITORY_ACCESS,
            )
            if pygithub_repo:
                return map_pygithub_repository_to_domain(pygithub_repo)
            return None
        except GITHUB_API_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(f"Failed to get repository {repo_full_name}", extra=sanitized)
            return None

    def _get_pygithub_repository(self, repo_full_name: str) -> PyGithubRepository | None:
        if not self._github_client:
            raise PRDifferException("GitHub client not initialized.", error_code=E5009_CONFIGURATION_ERROR)

        try:
            result = self._retry_handler.execute_with_retry(
                self._github_client.get_repo,
                repo_full_name,
                context=OperationContext.REPOSITORY_ACCESS,
            )
            return cast(PyGithubRepository | None, result)
        except GITHUB_API_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(f"Failed to get repository {repo_full_name}", extra=sanitized)
            return None

    def get_pull_request(self, repo_full_name: str, pr_number: int) -> PullRequest | None:
        if not self._github_client:
            raise PRDifferException(
                "GitHub client not initialized. Call initialize_client() before using get_pull_request().",
                error_code=E5009_CONFIGURATION_ERROR,
            )

        try:
            pygithub_repo = self._retry_handler.execute_with_retry(
                self._github_client.get_repo,
                repo_full_name,
                context=OperationContext.REPOSITORY_ACCESS,
            )
            if not pygithub_repo:
                return None

            pygithub_pr = self._retry_handler.execute_with_retry(pygithub_repo.get_pull, pr_number, context=OperationContext.PULL_REQUEST)
            if pygithub_pr:
                return map_pygithub_pr_to_domain(pygithub_pr)
            return None
        except GITHUB_API_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(f"Failed to get pull request #{pr_number}", extra=sanitized)
            return None

    def _get_pygithub_pull_request(self, pygithub_repo: PyGithubRepository, pr_number: int) -> PyGithubPullRequest | None:
        try:
            result = self._retry_handler.execute_with_retry(pygithub_repo.get_pull, pr_number, context=OperationContext.PULL_REQUEST)
            return cast(PyGithubPullRequest | None, result)
        except GITHUB_API_EXCEPTIONS as e:
            exc = cast(Exception, e)
            sanitized = sanitize_exception_for_logging(exc)
            self._logger.error(f"Failed to get pull request #{pr_number}", extra=sanitized)
            return None

    def _is_cache_entry_valid(self, cache_key: tuple[str, str]) -> bool:
        if cache_key not in self._file_content_cache:
            return False
        entry = self._file_content_cache[cache_key]
        age = time.time() - float(entry["timestamp"])
        return bool(age < self._cache_ttl)

    def _evict_oldest_entries(self) -> None:
        current_time = time.time()

        expired_keys: list[tuple[str, str]] = []
        for key, entry in self._file_content_cache.items():
            age = current_time - float(entry["timestamp"])
            if age >= self._cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            self._file_content_cache.pop(key)
            self._cache_evictions_ttl += 1

        if expired_keys:
            self._logger.debug(
                f"Cache eviction (TTL): removed {len(expired_keys)} expired entries [size={len(self._file_content_cache)}/{self._cache_max_size}]"
            )

        while len(self._file_content_cache) >= self._cache_max_size:
            evicted_key, _ = self._file_content_cache.popitem(last=False)
            self._cache_evictions_size += 1
            self._cache_evictions += 1
            self._logger.debug(f"Cache eviction (LRU): {evicted_key[0][:50]}... [size={len(self._file_content_cache)}/{self._cache_max_size}]")

    def _cache_set(self, cache_key: tuple[str, str], content: str) -> None:
        if cache_key in self._file_content_cache:
            del self._file_content_cache[cache_key]
        else:
            self._evict_oldest_entries()

        self._file_content_cache[cache_key] = {
            "content": content,
            "timestamp": time.time(),
        }

    def _cache_get(self, cache_key: tuple[str, str]) -> str | None:
        if not self._is_cache_entry_valid(cache_key):
            if cache_key in self._file_content_cache:
                del self._file_content_cache[cache_key]
            self._cache_misses += 1
            return None

        self._file_content_cache.move_to_end(cache_key)
        self._cache_hits += 1
        return str(self._file_content_cache[cache_key]["content"])

    def get_file_content(self, repo_full_name: str, file_path: str, branch: str) -> str:
        if not self._github_client:
            raise PRDifferException(
                "GitHub client not initialized. Call initialize_client() before using get_file_content().",
                error_code=E5009_CONFIGURATION_ERROR,
            )

        cache_key = (file_path, branch)
        cached_content = self._cache_get(cache_key)
        if cached_content is not None:
            return cached_content

        try:
            pygithub_repo = self._retry_handler.execute_with_retry(
                self._github_client.get_repo,
                repo_full_name,
                context=OperationContext.REPOSITORY_ACCESS,
            )
            if not pygithub_repo:
                return ""

            content = self._retry_handler.execute_with_retry(
                pygithub_repo.get_contents,
                file_path,
                ref=branch,
                context=OperationContext.FILE_CONTENT,
            )

            if isinstance(content, list):
                self._logger.warning(f"Expected single file but got directory for path '{file_path}' in branch '{branch}'. Found {len(content)} items.")
                file_content = ""
            else:
                file_content = self._extract_file_content(content)

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
            self._cache_set(cache_key, file_content)
            return file_content

    def get_files_content_batch(self, repo_full_name: str, file_paths: list[str], branch: str) -> dict[str, str]:
        results: dict[str, str] = {}
        files_to_fetch: list[str] = []

        for file_path in file_paths:
            cache_key = (file_path, branch)
            cached_content = self._cache_get(cache_key)
            if cached_content is not None:
                results[file_path] = cached_content
            else:
                files_to_fetch.append(file_path)

        for file_path in files_to_fetch:
            content = self.get_file_content(repo_full_name, file_path, branch)
            results[file_path] = content

        return results

    async def _get_file_content_async(self, repo_full_name: str, file_path: str, branch: str) -> str:
        if not self._github_client:
            raise PRDifferException(
                "GitHub client not initialized. Call initialize_client() before using _get_file_content_async().",
                error_code=E5009_CONFIGURATION_ERROR,
            )

        assert self._github_client is not None
        github_client = self._github_client

        cache_key = (file_path, branch)
        cached_content = self._cache_get(cache_key)
        if cached_content is not None:
            return cached_content

        try:

            async def get_repo_async():
                return await asyncer.asyncify(
                    lambda: self._retry_handler.execute_with_retry(
                        github_client.get_repo,
                        repo_full_name,
                        context=OperationContext.REPOSITORY_ACCESS,
                    )
                )()

            pygithub_repo = await get_repo_async()
            if not pygithub_repo:
                return ""

            async def get_contents_async():
                return await asyncer.asyncify(
                    lambda: self._retry_handler.execute_with_retry(
                        pygithub_repo.get_contents,
                        file_path,
                        ref=branch,
                        context=OperationContext.FILE_CONTENT,
                    )
                )()

            content = await get_contents_async()

            if isinstance(content, list):
                self._logger.warning(f"Expected single file but got directory for path '{file_path}' in branch '{branch}'. Found {len(content)} items.")
                file_content = ""
            else:
                file_content = self._extract_file_content(content)

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
            self._cache_set(cache_key, file_content)
            return file_content

    async def _get_files_content_batch_parallel_async(
        self,
        repo_full_name: str,
        file_paths: list[str],
        branch: str,
        max_workers: int = 4,
    ) -> dict[str, str]:
        results: dict[str, str] = {}
        files_to_fetch: list[str] = []

        for file_path in file_paths:
            cache_key = (file_path, branch)
            cached_content = self._cache_get(cache_key)
            if cached_content is not None:
                results[file_path] = cached_content
            else:
                files_to_fetch.append(file_path)

        if not files_to_fetch:
            return results

        start_time = time.time()
        fetched_contents = await self._async_executor.execute_batch(
            lambda fp: self._get_file_content_async(repo_full_name, fp, branch),
            files_to_fetch,
        )

        for file_path, content in zip(files_to_fetch, fetched_contents):
            results[file_path] = content

        elapsed = time.time() - start_time
        self._logger.debug(f"Async parallel batch fetch: {len(files_to_fetch)} files in {elapsed:.2f}s ({elapsed / len(files_to_fetch) * 1000:.1f}ms/file avg)")

        return results

    def _extract_file_content(self, content: ContentFile) -> str:
        if content and hasattr(content, "decoded_content") and content.decoded_content:
            return str(content.decoded_content.decode())
        return ""

    def get_etag_stats(self) -> dict[str, Any]:
        return self._etag_request_adapter.get_stats()

    def clear_etag_cache(self) -> None:
        self._etag_request_adapter.clear_cache()


def get_github_api_client(
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
    rate_limit_remaining_threshold: int | None = None,
    rate_limit_reset_buffer: float | None = None,
    secondary_rate_limit_backoff: float | None = None,
    api_health_tracking: bool = True,
    context_aware_retry: bool = True,
    use_advanced_retry: bool = True,
) -> GitHubAPIClient:
    if rate_limit_remaining_threshold is None or rate_limit_reset_buffer is None or secondary_rate_limit_backoff is None:
        from prdiffer.infrastructure.settings import get_settings_service

        settings_service = get_settings_service()
        if rate_limit_remaining_threshold is None:
            rate_limit_remaining_threshold = int(settings_service.get("github.retry.rate_limit_remaining_threshold", 1))
        if rate_limit_reset_buffer is None:
            rate_limit_reset_buffer = float(settings_service.get("github.retry.rate_limit_reset_buffer", 1.0))
        if secondary_rate_limit_backoff is None:
            secondary_rate_limit_backoff = float(settings_service.get("github.retry.secondary_rate_limit_backoff", 60.0))

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
        rate_limit_remaining_threshold=rate_limit_remaining_threshold,
        rate_limit_reset_buffer=rate_limit_reset_buffer,
        secondary_rate_limit_backoff=secondary_rate_limit_backoff,
        api_health_tracking=api_health_tracking,
        context_aware_retry=context_aware_retry,
        use_advanced_retry=use_advanced_retry,
    )
