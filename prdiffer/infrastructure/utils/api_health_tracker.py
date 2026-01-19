"""API health tracking for adaptive retry strategies."""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import deque
from prdiffer.infrastructure.logging.console_logger import get_logger


@dataclass
class APICall:
    """Represents an API call for health tracking."""

    timestamp: float
    duration: float
    success: bool
    error_type: Optional[str] = None


class APIHealthTracker:
    """Tracks API health metrics for adaptive retry strategies.

    Monitors API response times, success rates, and error patterns to inform
    intelligent retry decisions and adaptive delays.
    """

    def __init__(
        self,
        window_size: int = 100,
        time_window: float = 300.0,  # 5 minutes
        logger=None,
    ):
        """Initialize the API health tracker.

        Args:
            window_size: Maximum number of calls to track
            time_window: Time window in seconds for health calculations
            logger: Logger instance for health events
        """
        self.window_size = window_size
        self.time_window = time_window
        self._logger = logger or get_logger()

        # Store recent API calls
        self._calls: deque[APICall] = deque(maxlen=window_size)

        # Health metrics cache
        self._last_health_check = 0.0
        self._cached_health_score: Optional[float] = None

    def record_call(
        self, duration: float, success: bool, error_type: Optional[str] = None
    ):
        """Record an API call for health tracking.

        Args:
            duration: Call duration in seconds
            success: Whether the call was successful
            error_type: Type of error if call failed
        """
        call = APICall(
            timestamp=time.time(),
            duration=duration,
            success=success,
            error_type=error_type,
        )
        self._calls.append(call)

        # Invalidate cached health score
        self._cached_health_score = None

    def get_health_score(self) -> float:
        """Calculate current API health score (0.0 to 1.0).

        Returns:
            float: Health score where 1.0 is perfect health, 0.0 is completely unhealthy
        """
        current_time = time.time()

        # Use cached score if recent
        if (
            self._cached_health_score is not None
            and current_time - self._last_health_check < 10.0
        ):  # Cache for 10 seconds
            return self._cached_health_score

        # Calculate fresh health score
        recent_calls = self._get_recent_calls(current_time)

        if not recent_calls:
            # No recent calls, assume healthy
            self._cached_health_score = 1.0
        else:
            success_rate = sum(1 for call in recent_calls if call.success) / len(
                recent_calls
            )
            avg_duration = sum(call.duration for call in recent_calls) / len(
                recent_calls
            )

            # Health score based on success rate and response time
            # Success rate contributes 70%, response time contributes 30%
            success_component = success_rate * 0.7

            # Response time component (penalize slow responses)
            # Assume 1 second is good, 5+ seconds is bad
            time_component = max(0, 1 - (avg_duration - 1) / 4) * 0.3

            self._cached_health_score = max(
                0.0, min(1.0, success_component + time_component)
            )

        self._last_health_check = current_time
        return self._cached_health_score

    def get_recommended_delay(
        self, base_delay: float, max_delay: float = 30.0
    ) -> float:
        """Get recommended retry delay based on API health.

        Args:
            base_delay: Base retry delay
            max_delay: Maximum allowed delay

        Returns:
            float: Recommended delay in seconds
        """
        health_score = self.get_health_score()

        # Poor health = longer delays
        # Health score of 1.0 uses base_delay
        # Health score of 0.0 uses max_delay
        delay_multiplier = 1 + (1 - health_score) * (max_delay / base_delay - 1)

        recommended_delay = base_delay * delay_multiplier
        return min(recommended_delay, max_delay)

    def should_use_circuit_breaker(self) -> bool:
        """Determine if circuit breaker should be triggered based on health.

        Returns:
            bool: True if circuit breaker should be used
        """
        health_score = self.get_health_score()
        recent_calls = self._get_recent_calls(time.time())

        # Trigger circuit breaker if health is very poor and we have recent failures
        if health_score < 0.3 and len(recent_calls) >= 5:
            recent_failures = sum(1 for call in recent_calls[-5:] if not call.success)
            return recent_failures >= 4  # 4 out of last 5 calls failed

        return False

    def get_error_pattern(self) -> Dict[str, int]:
        """Get recent error patterns.

        Returns:
            dict: Error types and their counts
        """
        recent_calls = self._get_recent_calls(time.time())
        error_counts: Dict[str, int] = {}

        for call in recent_calls:
            if not call.success and call.error_type:
                error_counts[call.error_type] = error_counts.get(call.error_type, 0) + 1

        return error_counts

    def _get_recent_calls(self, current_time: float) -> List[APICall]:
        """Get calls within the time window.

        Args:
            current_time: Current timestamp

        Returns:
            list: Recent API calls within time window
        """
        cutoff_time = current_time - self.time_window
        return [call for call in self._calls if call.timestamp >= cutoff_time]

    def get_stats(self) -> dict:
        """Get comprehensive health statistics.

        Returns:
            dict: Health statistics
        """
        current_time = time.time()
        recent_calls = self._get_recent_calls(current_time)

        if not recent_calls:
            return {
                "health_score": 1.0,
                "total_calls": 0,
                "success_rate": 1.0,
                "avg_duration": 0.0,
                "error_patterns": {},
            }

        successful_calls = [call for call in recent_calls if call.success]

        return {
            "health_score": self.get_health_score(),
            "total_calls": len(recent_calls),
            "success_rate": len(successful_calls) / len(recent_calls),
            "avg_duration": sum(call.duration for call in recent_calls)
            / len(recent_calls),
            "error_patterns": self.get_error_pattern(),
            "window_size": self.window_size,
            "time_window": self.time_window,
        }


def get_api_health_tracker(
    window_size: int = 100, time_window: float = 300.0
) -> APIHealthTracker:
    """Get a configured API health tracker instance.

    Args:
        window_size: Maximum number of calls to track
        time_window: Time window in seconds for health calculations

    Returns:
        APIHealthTracker: Configured health tracker instance
    """
    return APIHealthTracker(window_size=window_size, time_window=time_window)
