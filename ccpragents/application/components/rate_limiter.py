"""Rate limiting component for request throttling."""

import time
import logging
from typing import List, Optional, Any
from ..interfaces.protocols import RateLimiterProtocol


class RateLimiter(RateLimiterProtocol):
    """Component responsible for rate limiting functionality."""

    def __init__(self, logger: Optional[Any] = None):
        """Initialize rate limiter.

        Args:
            logger: Optional logger instance
        """
        self._logger = logger or logging.getLogger(__name__)

        # Rate limiting configuration
        self._rate_limit_requests = 100  # Max requests per minute
        self._rate_limit_window = 60  # 60 second window
        self._request_timestamps: List[float] = []  # Track request timestamps for rate limiting

    def check_rate_limit(self, identifier: str) -> bool:
        """Check if the current request exceeds rate limits.

        Args:
            identifier: Unique identifier for rate limiting (currently not used in simple implementation)

        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()

        # Remove timestamps outside the rate limit window
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if current_time - ts < self._rate_limit_window
        ]

        # Check if we've exceeded the rate limit
        if len(self._request_timestamps) >= self._rate_limit_requests:
            self._logger.warning(
                f"Rate limit exceeded for {identifier}. Maximum {self._rate_limit_requests} "
                f"requests per {self._rate_limit_window} seconds. Current rate: {len(self._request_timestamps)}"
            )
            return False

        return True

    def increment_rate_limit(self, identifier: str) -> None:
        """Increment the rate limit counter for the identifier.

        Args:
            identifier: Unique identifier for rate limiting (currently not used in simple implementation)
        """
        current_time = time.time()
        self._request_timestamps.append(current_time)

        self._logger.debug(
            f"Rate limit incremented for {identifier}. Current rate: {len(self._request_timestamps)}/{self._rate_limit_requests}"
        )

    def get_current_rate(self) -> int:
        """Get current number of requests in the rate limit window.

        Returns:
            Number of requests in current window
        """
        current_time = time.time()

        # Clean up old timestamps
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if current_time - ts < self._rate_limit_window
        ]

        return len(self._request_timestamps)

    def get_rate_limit_info(self) -> dict:
        """Get rate limit configuration and current status.

        Returns:
            Dictionary with rate limit information
        """
        return {
            "max_requests": self._rate_limit_requests,
            "window_seconds": self._rate_limit_window,
            "current_requests": self.get_current_rate(),
            "remaining_requests": max(0, self._rate_limit_requests - self.get_current_rate())
        }