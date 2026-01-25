"""Rate limiting component for request throttling."""

import time
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict
from prdiffer.domain.interfaces.protocols import RateLimiterProtocol


class RateLimiter(RateLimiterProtocol):
    """Component responsible for rate limiting functionality.

    Implements per-client rate limiting using the identifier parameter.
    Each client (identified by API key, IP address, or other unique identifier)
    has their own rate limit tracking.
    """

    def __init__(self, logger: Optional[Any] = None):
        """Initialize rate limiter.

        Args:
            logger: Optional logger instance
        """
        self._logger = logger or logging.getLogger(__name__)

        # Rate limiting configuration
        self._rate_limit_requests = 100  # Max requests per minute per client
        self._rate_limit_window = 60  # 60 second window
        # Track request timestamps per client identifier
        self._client_timestamps: Dict[str, List[float]] = defaultdict(list)
        # Track last access time for cleanup
        self._last_access: Dict[str, float] = {}

        # Cleanup configuration
        self._cleanup_interval = 300  # Cleanup every 5 minutes
        self._client_ttl = 3600  # Remove clients after 1 hour of inactivity

    def check_rate_limit(self, identifier: str) -> bool:
        """Check if the current request exceeds rate limits for the client.

        Args:
            identifier: Unique identifier for rate limiting (API key, IP address, etc.)

        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()

        # Periodic cleanup of old entries
        if current_time % self._cleanup_interval < 1:
            self._cleanup_old_entries(current_time)

        # Get timestamps for this client
        timestamps = self._client_timestamps[identifier]

        # Remove timestamps outside the rate limit window
        self._client_timestamps[identifier] = [
            ts for ts in timestamps if current_time - ts < self._rate_limit_window
        ]

        # Update last access time
        self._last_access[identifier] = current_time

        # Check if we've exceeded the rate limit
        current_count = len(self._client_timestamps[identifier])
        if current_count >= self._rate_limit_requests:
            self._logger.warning(
                f"Rate limit exceeded for client '{identifier}'. "
                f"Maximum {self._rate_limit_requests} requests per {self._rate_limit_window} "
                f"seconds. Current rate: {current_count}"
            )
            return False

        return True

    def increment_rate_limit(self, identifier: str) -> None:
        """Increment the rate limit counter for the identifier.

        Args:
            identifier: Unique identifier for rate limiting
        """
        current_time = time.time()
        self._client_timestamps[identifier].append(current_time)

        current_count = len(self._client_timestamps[identifier])
        self._logger.debug(
            f"Rate limit incremented for client '{identifier}'. "
            f"Current rate: {current_count}/{self._rate_limit_requests}"
        )

    def get_current_rate(self, identifier: str = "global") -> int:
        """Get current number of requests in the rate limit window for a client.

        Args:
            identifier: Client identifier to check rate for (default: "global" returns max across all clients)

        Returns:
            Number of requests in current window for the specified client
        """
        current_time = time.time()

        if identifier == "global":
            # Return the maximum rate across all clients
            return max(
                (
                    len(
                        [
                            ts
                            for ts in timestamps
                            if current_time - ts < self._rate_limit_window
                        ]
                    )
                    for timestamps in self._client_timestamps.values()
                ),
                default=0,
            )

        # Clean up old timestamps for this client
        timestamps = self._client_timestamps.get(identifier, [])
        self._client_timestamps[identifier] = [
            ts for ts in timestamps if current_time - ts < self._rate_limit_window
        ]

        return len(self._client_timestamps[identifier])

    def get_rate_limit_info(self, identifier: str = "global") -> dict:
        """Get rate limit configuration and current status for a client.

        Args:
            identifier: Client identifier to get info for (default: "global")

        Returns:
            Dictionary with rate limit information
        """
        current_requests = self.get_current_rate(identifier)
        return {
            "max_requests": self._rate_limit_requests,
            "window_seconds": self._rate_limit_window,
            "current_requests": current_requests,
            "remaining_requests": max(0, self._rate_limit_requests - current_requests),
            "identifier": identifier,
        }

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old client entries to prevent memory leaks.

        Args:
            current_time: Current timestamp for comparison
        """
        # Remove entries older than TTL
        expired_identifiers = [
            identifier
            for identifier, last_access in self._last_access.items()
            if current_time - last_access > self._client_ttl
        ]

        for identifier in expired_identifiers:
            del self._client_timestamps[identifier]
            del self._last_access[identifier]

        if expired_identifiers:
            self._logger.debug(
                f"Cleaned up {len(expired_identifiers)} expired rate limit entries"
            )

    def get_active_clients_count(self) -> int:
        """Get the number of active clients tracked.

        Returns:
            Number of clients with recent activity
        """
        return len(self._client_timestamps)

    def reset_client(self, identifier: str) -> bool:
        """Reset rate limit tracking for a specific client.

        Args:
            identifier: Client identifier to reset

        Returns:
            True if the client was found and reset
        """
        if identifier in self._client_timestamps:
            del self._client_timestamps[identifier]
            del self._last_access[identifier]
            self._logger.info(f"Reset rate limit for client '{identifier}'")
            return True
        return False

    def get_all_client_info(self) -> Dict[str, Dict[str, Any]]:
        """Get rate limit information for all active clients.

        Returns:
            Dictionary mapping client identifiers to their rate limit info
        """
        current_time = time.time()
        result = {}

        for identifier, timestamps in self._client_timestamps.items():
            # Count requests within the window
            valid_timestamps = [
                ts for ts in timestamps if current_time - ts < self._rate_limit_window
            ]
            result[identifier] = {
                "current_requests": len(valid_timestamps),
                "max_requests": self._rate_limit_requests,
                "remaining_requests": max(
                    0, self._rate_limit_requests - len(valid_timestamps)
                ),
                "last_access": self._last_access.get(identifier, current_time),
            }

        return result
