"""ETag HTTP adapter for GitHub API conditional requests.

Reduces bandwidth by using If-None-Match headers and handling 304 Not Modified
responses with cached content.
"""

import time
import logging
import threading
from collections import OrderedDict
from typing import Any
from prdiffer.infrastructure.logging.console_logger import get_logger, ConsoleLogger


class ETagRequestAdapter:
    """ETag HTTP adapter managing conditional requests via If-None-Match headers.

    Thread Safety:
    - ETag cache operations are not protected by locks (relies on external cache service's locking)
    """

    HTTP_NOT_MODIFIED = 304

    def __init__(
        self,
        cache_service: Any,
        enabled: bool = True,
        etag_ttl: int = 600,
        etag_cache_size: int = 1000,
        logger: logging.Logger | ConsoleLogger | None = None,
    ) -> None:
        self._enabled = enabled
        self._etag_ttl = etag_ttl
        self._etag_cache_size = etag_cache_size
        self._logger = logger or get_logger()

        self._cache_service = cache_service

        self._etag_cache: dict[str, str] = OrderedDict()

        self._stats_lock = threading.Lock()
        self._etag_hits = 0
        self._etag_misses = 0
        self._not_modified_responses = 0

    def _get_cache_key(self, url: str) -> str:
        return url

    def _get_etag(self, cache_key: str) -> str | None:
        if self._cache_service:
            return self._cache_service.get_etag(cache_key)
        return None

    def _store_etag(self, cache_key: str, etag: str, commit_sha: str | None = None) -> None:
        if self._cache_service:
            self._cache_service.set_etag(cache_key, etag, commit_sha)
            cache_entry = self._cache_service.get(cache_key)
            if cache_entry and cache_entry.get("timestamp"):
                cache_entry["timestamp"] = time.time()

    def clear_cache(self) -> None:
        self._etag_cache.clear()
        self._logger.info("ETag cache cleared")

    def get_stats(self) -> dict[str, Any]:
        with self._stats_lock:
            total_requests = self._etag_hits + self._etag_misses
            hit_rate = self._etag_hits * 100 / total_requests if total_requests else 0.0

            etag_hits = self._etag_hits
            etag_misses = self._etag_misses
            not_modified_responses = self._not_modified_responses

        return {
            "enabled": self._enabled,
            "cache_size": len(self._etag_cache),
            "max_cache_size": self._etag_cache_size,
            "ttl_seconds": self._etag_ttl,
            "etag_hits": etag_hits,
            "etag_misses": etag_misses,
            "not_modified_responses": not_modified_responses,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def add_if_none_match_header(self, url: str, headers: dict[str, str]) -> dict[str, str]:
        if not self._enabled:
            return headers

        etag = self._get_etag(url)
        if etag:
            headers["If-None-Match"] = etag
            self._logger.debug(f"Added If-None-Match header for {url[:60]}... (etag={etag})")
        return headers

    def handle_etag_response(self, url: str, status_code: int, headers: dict[str, str], content: str) -> str:
        if not self._enabled:
            return content

        etag = headers.get("ETag")

        if status_code == self.HTTP_NOT_MODIFIED:
            with self._stats_lock:
                self._not_modified_responses += 1
                self._etag_hits += 1
            cached_content = self._cache_service.get(url) if self._cache_service else None

            if cached_content is not None:
                self._logger.info(f"304 Not Modified - returning cached content for {url[:60]}... (etag={etag})")
                return cached_content
            else:
                self._logger.warning(f"304 response but no cached content for {url[:60]}...")
                return ""

        if etag:
            self._store_etag(url, etag, content)
            with self._stats_lock:
                self._etag_misses += 1
        elif status_code == 200:
            self._logger.debug(f"200 response without ETag for {url[:60]}...")

        return content
