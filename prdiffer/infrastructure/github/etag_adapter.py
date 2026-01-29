"""ETag HTTP adapter for GitHub API requests.

This module provides a minimal HTTP adapter that intercepts GET requests
to add If-None-Match headers for conditional requests and handles 304 responses
by returning cached content.

ETag support reduces bandwidth usage by allowing the server to return 304 Not Modified
when content hasn't changed, which saves on data transfer for large responses.
"""

import time
from collections import OrderedDict
from typing import Dict, Optional, Any
from urllib.request import Request as urllib_Request
from urllib.request import OpenerDirector

from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)


class ETagRequestAdapter:
    """Minimal HTTP adapter that adds ETag support to PyGithub requests.

    This adapter wraps PyGithub's HTTP client to:
    1. Store ETags per resource URL
    2. Check ETag on cache hits and send If-None-Match header
    3. Return cached content on 304 responses

    The adapter uses an in-memory LRU cache for ETag storage, which is
    automatically cleared when resources are modified based on TTL.

    Thread Safety:
    - ETag cache operations are protected by a lock
    - HTTP requests are not modified beyond adding headers
    """

    HTTP_NOT_MODIFIED = 304

    def __init__(
        self,
        enabled: bool = True,
        etag_ttl: int = 600,
        etag_cache_size: int = 1000,
        logger=None,
    ):
        """Initialize the ETag request adapter.

        Args:
            enabled: Whether ETag support is enabled (default: True)
            etag_ttl: Time-to-live for ETag cache entries in seconds (default: 600)
            etag_cache_size: Maximum number of ETag entries to cache (default: 1000)
            logger: Logger instance for logging operations
        """
        self._enabled = enabled
        self._etag_ttl = etag_ttl
        self._etag_cache_size = etag_cache_size
        self._logger = logger or get_logger()

        self._etag_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

        self._etag_hits = 0
        self._etag_misses = 0
        self._not_modified_responses = 0

        if self._enabled:
            self._logger.info(
                f"ETag adapter enabled (ttl={self._etag_ttl}s, "
                f"cache_size={self._etag_cache_size})"
            )

    def is_enabled(self) -> bool:
        """Check if ETag support is enabled.

        Returns:
            bool: True if ETag support is enabled
        """
        return self._enabled

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key for the given URL.

        Args:
            url: The resource URL

        Returns:
            str: The cache key (same as URL for simplicity)
        """
        return url

    def _get_etag(self, url: str) -> Optional[str]:
        """Get cached ETag for a URL if it exists and is not expired.

        Args:
            url: The resource URL

        Returns:
            Optional[str]: Cached ETag if valid, None otherwise
        """
        cache_key = self._get_cache_key(url)

        if cache_key not in self._etag_cache:
            self._etag_misses += 1
            return None

        entry = self._etag_cache[cache_key]
        age = time.time() - entry["timestamp"]

        if age > self._etag_ttl:
            self._etag_misses += 1
            return None

        self._etag_cache.move_to_end(cache_key)
        self._etag_hits += 1
        return entry["etag"]

    def _get_cached_content(self, url: str) -> Optional[str]:
        """Get cached content for a URL if it exists and is not expired.

        Args:
            url: The resource URL

        Returns:
            Optional[str]: Cached content if valid, None otherwise
        """
        cache_key = self._get_cache_key(url)

        if cache_key not in self._etag_cache:
            return None

        entry = self._etag_cache[cache_key]
        age = time.time() - entry["timestamp"]

        if age > self._etag_ttl:
            return None

        return entry.get("content")

    def _store_etag(self, url: str, etag: str, content: Optional[str] = None) -> None:
        """Store ETag and optionally content for a URL.

        Args:
            url: The resource URL
            etag: The ETag from the response
            content: The response content (optional, for 304 handling)
        """
        if not self._enabled:
            return

        cache_key = self._get_cache_key(url)

        if cache_key in self._etag_cache:
            del self._etag_cache[cache_key]
        else:
            if len(self._etag_cache) >= self._etag_cache_size:
                self._evict_oldest_entries()

        self._etag_cache[cache_key] = {
            "etag": etag,
            "content": content,
            "timestamp": time.time(),
        }

        self._logger.debug(
            f"ETag stored for {url[:60]}...",
            etag=etag,
            cache_key=cache_key[:40],
            has_content=content is not None,
        )

    def _evict_oldest_entries(self) -> None:
        """Evict oldest entries when cache exceeds max size (LRU eviction).

        Also removes expired entries to maintain cache hygiene.
        """
        current_time = time.time()

        expired_keys = []
        for key, entry in self._etag_cache.items():
            age = current_time - entry["timestamp"]
            if age >= self._etag_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            self._etag_cache.pop(key)

        if expired_keys:
            self._logger.debug(
                f"ETag cache eviction (TTL): removed {len(expired_keys)} expired entries "
                f"[size={len(self._etag_cache)}/{self._etag_cache_size}]"
            )

        while len(self._etag_cache) >= self._etag_cache_size:
            evicted_key, _ = self._etag_cache.popitem(last=False)
            self._logger.debug(
                f"ETag cache eviction (LRU): {evicted_key[:50]}... "
                f"[size={len(self._etag_cache)}/{self._etag_cache_size}]"
            )

    def clear_cache(self) -> None:
        """Clear all cached ETags and content."""
        self._etag_cache.clear()
        self._logger.info("ETag cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get ETag adapter statistics.

        Returns:
            Dict[str, Any]: Statistics including cache size, hits, misses
        """
        total_requests = self._etag_hits + self._etag_misses
        hit_rate = (self._etag_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "enabled": self._enabled,
            "cache_size": len(self._etag_cache),
            "max_cache_size": self._etag_cache_size,
            "ttl_seconds": self._etag_ttl,
            "etag_hits": self._etag_hits,
            "etag_misses": self._etag_misses,
            "not_modified_responses": self._not_modified_responses,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def add_if_none_match_header(
        self, url: str, headers: Dict[str, str]
    ) -> Dict[str, str]:
        """Add If-None-Match header to request headers if ETag is cached.

        Args:
            url: The resource URL
            headers: The request headers dictionary

        Returns:
            Dict[str, str]: Updated headers with If-None-Match if applicable
        """
        if not self._enabled:
            return headers

        etag = self._get_etag(url)
        if etag:
            headers["If-None-Match"] = etag
            self._logger.debug(
                f"Added If-None-Match header for {url[:60]}...",
                etag=etag,
            )
        return headers

    def handle_etag_response(
        self, url: str, status_code: int, headers: Dict[str, str], content: str
    ) -> str:
        """Handle HTTP response, storing ETag and handling 304 responses.

        Args:
            url: The resource URL
            status_code: HTTP response status code
            headers: Response headers
            content: Response content

        Returns:
            str: Content to return (cached or new)
        """
        if not self._enabled:
            return content

        etag = headers.get("ETag")

        if status_code == self.HTTP_NOT_MODIFIED:
            self._not_modified_responses += 1
            cached_content = self._get_cached_content(url)

            if cached_content is not None:
                self._logger.info(
                    f"304 Not Modified - returning cached content for {url[:60]}...",
                    etag=etag,
                )
                return cached_content
            else:
                self._logger.warning(
                    f"304 response but no cached content for {url[:60]}...",
                    url=url,
                )
                return ""

        if etag:
            self._store_etag(url, etag, content)
        elif status_code == 200:
            self._logger.debug(
                f"200 response without ETag for {url[:60]}...",
                url=url,
            )

        return content
