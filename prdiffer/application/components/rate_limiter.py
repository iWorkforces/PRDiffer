"""Rate limiting component for request throttling."""

import time
import logging
from typing import Any
from collections import deque
from prdiffer.domain.interfaces.protocols import RateLimiterProtocol
from prdiffer.domain.services.logger import LoggerServiceInterface


class RateLimiter(RateLimiterProtocol):
    """Per-client rate limiting using bounded deques with automatic cleanup."""

    def __init__(self, logger: logging.Logger | LoggerServiceInterface | None = None):
        self._logger = logger or logging.getLogger(__name__)

        self._rate_limit_requests = 100  # Max requests per minute per client
        self._rate_limit_window = 60  # 60 second window
        self._max_timestamps_per_client = 200  # Maximum timestamps to track per client (DoS prevention)
        self._client_timestamps: dict[str, deque[float]] = {}
        self._last_access: dict[str, float] = {}

        self._cleanup_interval = 300  # Cleanup every 5 minutes
        self._client_ttl = 3600  # Remove clients after 1 hour of inactivity

    def check_rate_limit(self, identifier: str) -> bool:
        """Check if the request exceeds rate limits for the client.

        Returns True if allowed, False if rate limited.
        """
        current_time = time.time()

        if current_time % self._cleanup_interval < 1:
            self._cleanup_old_entries(current_time)

        if identifier not in self._client_timestamps:
            self._client_timestamps[identifier] = deque(maxlen=self._max_timestamps_per_client)

        timestamps = self._client_timestamps[identifier]

        self._client_timestamps[identifier] = deque(
            [ts for ts in timestamps if current_time - ts < self._rate_limit_window], maxlen=self._max_timestamps_per_client
        )

        self._last_access[identifier] = current_time

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
        """Record a request for the given identifier."""
        current_time = time.time()
        if identifier not in self._client_timestamps:
            self._client_timestamps[identifier] = deque(maxlen=self._max_timestamps_per_client)

        self._client_timestamps[identifier].append(current_time)

        current_count = len(self._client_timestamps.get(identifier, []))
        self._logger.debug(f"Rate limit incremented for client '{identifier}'. Current rate: {current_count}/{self._rate_limit_requests}")

    def get_current_rate(self, identifier: str = "global") -> int:
        """Get current request count in the rate limit window for a client."""
        current_time = time.time()

        if identifier == "global":
            return max(
                (len([ts for ts in timestamps if current_time - ts < self._rate_limit_window]) for timestamps in self._client_timestamps.values()),
                default=0,
            )

        if identifier in self._client_timestamps:
            timestamps = self._client_timestamps[identifier]
            self._client_timestamps[identifier] = deque(
                [ts for ts in timestamps if current_time - ts < self._rate_limit_window], maxlen=self._max_timestamps_per_client
            )

        return len(self._client_timestamps.get(identifier, []))

    def get_rate_limit_info(self, identifier: str = "global") -> dict[str, Any]:
        """Get rate limit configuration and current status for a client."""
        current_requests = self.get_current_rate(identifier)
        return {
            "max_requests": self._rate_limit_requests,
            "window_seconds": self._rate_limit_window,
            "current_requests": current_requests,
            "remaining_requests": max(0, self._rate_limit_requests - current_requests),
            "identifier": identifier,
        }

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Remove client entries older than TTL to prevent memory leaks."""
        expired_identifiers = [identifier for identifier, last_access in self._last_access.items() if current_time - last_access > self._client_ttl]

        for identifier in expired_identifiers:
            del self._client_timestamps[identifier]
            del self._last_access[identifier]

        if expired_identifiers:
            self._logger.debug(f"Cleaned up {len(expired_identifiers)} expired rate limit entries")

    def get_active_clients_count(self) -> int:
        """Get the number of active clients tracked."""
        return len(self._client_timestamps)

    def reset_client(self, identifier: str) -> bool:
        """Reset rate limit tracking for a specific client. Returns True if client was found."""
        if identifier in self._client_timestamps:
            del self._client_timestamps[identifier]
            del self._last_access[identifier]
            self._logger.info(f"Reset rate limit for client '{identifier}'")
            return True
        return False

    def get_all_client_info(self) -> dict[str, dict[str, Any]]:
        """Get rate limit information for all active clients."""
        current_time = time.time()
        result: dict[str, dict[str, Any]] = {}

        for identifier, timestamps in self._client_timestamps.items():
            valid_timestamps = [ts for ts in list(timestamps) if current_time - ts < self._rate_limit_window]
            result[identifier] = {
                "current_requests": len(valid_timestamps),
                "max_requests": self._rate_limit_requests,
                "remaining_requests": max(0, self._rate_limit_requests - len(valid_timestamps)),
                "last_access": self._last_access.get(identifier, current_time),
            }

        return result
