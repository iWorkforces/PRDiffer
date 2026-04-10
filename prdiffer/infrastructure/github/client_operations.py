"""GitHub API client operations (file content, caching, batch fetching).

Extracted from client.py for maintainability.
Contains file content retrieval, caching, and batch operations.
"""

from __future__ import annotations

import time
import asyncer
from collections import OrderedDict
from typing import Any, cast

from github import Github
from github.ContentFile import ContentFile

from prdiffer.infrastructure.utils.retry.models import OperationContext
from prdiffer.infrastructure.utils.retry.base import BaseUnifiedRetryHandler
from prdiffer.infrastructure.logging.console_logger import ConsoleLogger
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)
from prdiffer.domain.exceptions import PRDifferException
from prdiffer.domain.errors import E5009_CONFIGURATION_ERROR
from prdiffer.infrastructure.github.client_models import GITHUB_API_EXCEPTIONS
from prdiffer.infrastructure.utils.parallel.executor import AsyncParallelExecutor
from prdiffer.infrastructure.github.etag_adapter import ETagRequestAdapter


class GitHubAPIClientOperationsMixin:
    """Mixin providing file content operations and caching for GitHubAPIClient.

    Requires the host class to provide:
        - self._github_client: Github | None
        - self._logger: ConsoleLogger
        - self._retry_handler: retry handler
        - self._file_content_cache: OrderedDict
        - self._cache_max_size: int
        - self._cache_ttl: int
        - self._max_file_size_bytes: int
        - self._cache_hits: int
        - self._cache_misses: int
        - self._cache_evictions: int
        - self._cache_evictions_ttl: int
        - self._cache_evictions_size: int
        - self._async_executor: AsyncParallelExecutor
        - self._etag_request_adapter: ETagRequestAdapter
        - self._parallel_file_fetch_enabled: bool
    """

    # Type annotations for host class attributes used by this mixin
    _github_client: Github | None
    _retry_handler: BaseUnifiedRetryHandler
    _logger: ConsoleLogger
    _file_content_cache: OrderedDict[tuple[str, str], dict[str, Any]]
    _cache_ttl: float
    _cache_max_size: int
    _cache_hits: int
    _cache_misses: int
    _cache_evictions: int
    _cache_evictions_ttl: int
    _cache_evictions_size: int
    _parallel_file_fetch_enabled: bool
    _async_executor: AsyncParallelExecutor
    _max_file_size_bytes: int
    _etag_request_adapter: ETagRequestAdapter

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
        """Get content for multiple files with caching and optional parallel fetching."""
        if self._parallel_file_fetch_enabled:
            # Use anyio.run to call async method from sync context
            import anyio

            return anyio.run(
                self._get_files_content_batch_parallel_async,
                repo_full_name,
                file_paths,
                branch,
            )

        # Legacy sequential path (default)
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
        """Extract file content with size validation (DoS prevention).

        Handles files with encoding: none (binary files, submodules, empty files)
        by returning empty string instead of crashing on decoded_content access.
        """
        # Check encoding first - PyGithub's decoded_content asserts encoding == "base64"
        # GitHub returns encoding: none for binary files, submodules, empty files
        if not content:
            return ""

        encoding = getattr(content, "encoding", None)
        if encoding != "base64":
            # Log for debugging but don't crash - return empty content
            file_path = getattr(content, "path", "unknown")
            self._logger.debug(f"File '{file_path}' has non-base64 encoding '{encoding}'. Skipping content extraction.")
            return ""

        # Check file size before loading into memory (DoS prevention)
        if hasattr(content, "size") and content.size > self._max_file_size_bytes:
            file_path = getattr(content, "path", "unknown")
            self._logger.warning(
                f"File too large to load: {file_path} ({content.size} bytes > {self._max_file_size_bytes} bytes max). Skipping file to prevent OOM."
            )
            return ""

        # Now safe to access decoded_content - encoding is confirmed base64
        if content.decoded_content:
            return str(content.decoded_content.decode())
        return ""

    def get_etag_stats(self) -> dict[str, Any]:
        return self._etag_request_adapter.get_stats()

    def clear_etag_cache(self) -> None:
        self._etag_request_adapter.clear_cache()
