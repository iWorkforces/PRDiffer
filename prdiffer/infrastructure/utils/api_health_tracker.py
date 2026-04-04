"""API health tracking for adaptive retry strategies."""

import time
import logging
from typing import Any
from dataclasses import dataclass
from collections import deque
from prdiffer.infrastructure.logging.console_logger import get_logger


@dataclass
class APICall:
    """Represents an API call for health tracking."""

    timestamp: float
    duration: float
    success: bool
    error_type: str | None = None


class APIHealthTracker:
    """Tracks API health metrics for adaptive retry strategies."""

    def __init__(
        self,
        window_size: int = 100,
        time_window: float = 300.0,  # 5 minutes
        logger: logging.Logger | None = None,
    ) -> None:
        self.window_size = window_size
        self.time_window = time_window
        self._logger = logger or get_logger()

        self._calls: deque[APICall] = deque(maxlen=window_size)

        self._last_health_check = 0.0
        self._cached_health_score: float | None = None

    def record_call(self, duration: float, success: bool, error_type: str | None = None):
        """Record an API call for health tracking."""
        call = APICall(
            timestamp=time.time(),
            duration=duration,
            success=success,
            error_type=error_type,
        )
        self._calls.append(call)

        self._cached_health_score = None

    def get_health_score(self) -> float:
        """Calculate current API health score (0.0 to 1.0)."""
        current_time = time.time()

        if self._cached_health_score is not None and current_time - self._last_health_check < 10.0:  # Cache for 10 seconds
            return self._cached_health_score

        recent_calls = self._get_recent_calls(current_time)

        if not recent_calls:
            self._cached_health_score = 1.0
        else:
            success_rate = sum(1 for call in recent_calls if call.success) / len(recent_calls)
            avg_duration = sum(call.duration for call in recent_calls) / len(recent_calls)

            # Success rate 70%, response time 30%
            success_component = success_rate * 0.7

            # 1s = good, 5s+ = bad
            time_component = max(0, 1 - (avg_duration - 1) / 4) * 0.3

            self._cached_health_score = max(0.0, min(1.0, success_component + time_component))

        self._last_health_check = current_time
        return self._cached_health_score

    def get_recommended_delay(self, base_delay: float, max_delay: float = 30.0) -> float:
        """Get recommended retry delay based on API health."""
        health_score = self.get_health_score()

        delay_multiplier = 1 + (1 - health_score) * (max_delay / base_delay - 1)

        recommended_delay = base_delay * delay_multiplier
        return min(recommended_delay, max_delay)

    def get_error_pattern(self) -> dict[str, int]:
        """Get recent error patterns."""
        recent_calls = self._get_recent_calls(time.time())
        error_counts: dict[str, int] = {}

        for call in recent_calls:
            if not call.success and call.error_type:
                error_counts[call.error_type] = error_counts.get(call.error_type, 0) + 1

        return error_counts

    def _get_recent_calls(self, current_time: float) -> list[APICall]:
        """Get calls within the time window."""
        cutoff_time = current_time - self.time_window
        return [call for call in self._calls if call.timestamp >= cutoff_time]

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive health statistics."""
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
            "avg_duration": sum(call.duration for call in recent_calls) / len(recent_calls),
            "error_patterns": self.get_error_pattern(),
            "window_size": self.window_size,
            "time_window": self.time_window,
        }


def get_api_health_tracker(window_size: int = 100, time_window: float = 300.0) -> APIHealthTracker:
    """Get a configured API health tracker instance."""
    return APIHealthTracker(window_size=window_size, time_window=time_window)
