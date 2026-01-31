"""ETag HTTP adapter for GitHub API requests.

This module provides a minimal HTTP adapter that intercepts GET requests
to add If-None-Match headers for conditional requests and handles 304 responses
by returning cached content.

ETag support reduces bandwidth usage by allowing the server to return 304 Not Modified
when content hasn't changed, which saves on data transfer for large responses.
"""

import time
from collections import OrderedDict
from typing import Optional, Any

from prdiffer.infrastructure.logging.console_logger import get_logger


class ETagRequestAdapter:
    """ETag HTTP adapter for GitHub API requests.

    This adapter manages ETag-based conditional requests by:
    1. Storing ETags per resource URL
    2. Checking cache for ETags before requests
    3. Handling 304 Not Modified responses
    4. Integrating with external cache service for ETag storage

    Thread Safety:
    - ETag cache operations are not protected by locks (relies on external cache service's locking)
    """

    HTTP_NOT_MODIFIED = 304

    def __init__(
        self,
        cache_service,
        enabled: bool = True,
        etag_ttl: int = 600,
        etag_cache_size: int = 1000,
        logger=None,
    ):
        """Initialize the ETag request adapter.

        Args:
            cache_service: Cache service for ETag storage
            enabled: Whether ETag support is enabled (default: True)
            etag_ttl: Time-to-live for ETag cache entries in seconds (default: 600)
            etag_cache_size: Maximum number of ETag entries to cache (default: 1000)
            logger: Logger instance for logging operations
        """
        self._enabled = enabled
        self._etag_ttl = etag_ttl
        self._etag_cache_size = etag_cache_size
        self._logger = logger or get_logger()

        # External cache service reference (injected via dependency injection)
        self._cache_service = cache_service

        # ETag cache - stored as URL -> etag mapping for fast lookup
        self._etag_cache: dict[str, str] = OrderedDict()
        self._etag_hits = 0
        self._etag_misses = 0
        self._not_modified_responses = 0

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key for a given URL."""
        return url

    def _get_etag(self, cache_key: str) -> Optional[str]:
        """Get cached ETag from cache service."""
        if self._cache_service:
            return self._cache_service.get_etag(cache_key)
        return None

    def _store_etag(
        self, cache_key: str, etag: str, commit_sha: Optional[str] = None
    ) -> None:
        """Store ETag in cache service."""
        if self._cache_service:
            self._cache_service.set_etag(cache_key, etag, commit_sha)
            # Also update cache timestamp
            cache_entry = self._cache_service.get(cache_key)
            if cache_entry and cache_entry.get("timestamp"):
                cache_entry["timestamp"] = time.time()

    def clear_cache(self) -> None:
        """Clear all cached ETags and content."""
        self._etag_cache.clear()
        self._logger.info("ETag cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get ETag adapter statistics.

        Returns:
            dict[str, Any]: Statistics including cache size, hits, misses
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
        self, url: str, headers: dict[str, str]
    ) -> dict[str, str]:
        """Add If-None-Match header to request headers if ETag is cached.

        Args:
            url: The resource URL
            headers: The request headers dictionary

        Returns:
            dict[str, str]: Updated headers with If-None-Match if applicable
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
        self, url: str, status_code: int, headers: dict[str, str], content: str
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
            cached_content = (
                self._cache_service.get(url) if self._cache_service else None
            )

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
