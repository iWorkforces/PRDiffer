"""Metrics tracking component for request statistics and monitoring."""

import time
import logging
from typing import Dict, Any, Optional
from ..interfaces.protocols import MetricsTrackerProtocol


class MetricsTracker(MetricsTrackerProtocol):
    """Component responsible for tracking metrics and request statistics."""

    def __init__(self, logger: Optional[Any] = None):
        """Initialize metrics tracker.

        Args:
            logger: Optional logger instance
        """
        self._logger = logger or logging.getLogger(__name__)

        # Request tracking for structured logging
        self._request_counter = 0

        # Metrics tracking
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._start_time = time.time()

        # Operation-specific metrics
        self._operation_metrics: Dict[str, Dict[str, Any]] = {}

    def track_request(
        self, operation: str, success: bool, execution_time: float
    ) -> None:
        """Track a request for metrics collection.

        Args:
            operation: Name of the operation being tracked
            success: Whether the operation was successful
            execution_time: Time taken to execute the operation in seconds
        """
        self._total_requests += 1

        if success:
            self._successful_requests += 1
        else:
            self._failed_requests += 1

        # Track operation-specific metrics
        if operation not in self._operation_metrics:
            self._operation_metrics[operation] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_execution_time": 0.0,
                "min_execution_time": float("inf"),
                "max_execution_time": 0.0,
            }

        op_metrics = self._operation_metrics[operation]
        op_metrics["total_requests"] += 1

        if success:
            op_metrics["successful_requests"] += 1
        else:
            op_metrics["failed_requests"] += 1

        op_metrics["total_execution_time"] += execution_time
        op_metrics["min_execution_time"] = min(
            op_metrics["min_execution_time"], execution_time
        )
        op_metrics["max_execution_time"] = max(
            op_metrics["max_execution_time"], execution_time
        )

        self._logger.debug(
            f"Request tracked - operation: {operation}, success: {success}, execution_time: {execution_time:.3f}s, total_requests: {self._total_requests}"
        )

    def generate_request_id(self) -> str:
        """Generate a unique request ID for tracking purposes.

        Returns:
            Unique request ID in format REQ-{timestamp}-{counter}
        """
        self._request_counter += 1
        return f"REQ-{int(time.time() * 1000)}-{self._request_counter}"

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of collected metrics.

        Returns:
            Dictionary containing metrics data
        """
        current_time = time.time()
        uptime_seconds = current_time - self._start_time

        metrics = {
            "uptime_seconds": uptime_seconds,
            "uptime_human": self._format_uptime(uptime_seconds),
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "success_rate": self._calculate_success_rate(),
            "operations": {},
        }

        # Add operation-specific metrics with calculated averages
        for operation, op_metrics in self._operation_metrics.items():
            avg_execution_time = 0.0
            if op_metrics["total_requests"] > 0:
                avg_execution_time = (
                    op_metrics["total_execution_time"] / op_metrics["total_requests"]
                )

            success_rate = 0.0
            if op_metrics["total_requests"] > 0:
                success_rate = (
                    op_metrics["successful_requests"] / op_metrics["total_requests"]
                ) * 100

            metrics["operations"][operation] = {
                "total_requests": op_metrics["total_requests"],
                "successful_requests": op_metrics["successful_requests"],
                "failed_requests": op_metrics["failed_requests"],
                "success_rate": round(success_rate, 2),
                "avg_execution_time": round(avg_execution_time, 3),
                "min_execution_time": round(op_metrics["min_execution_time"], 3)
                if op_metrics["min_execution_time"] != float("inf")
                else 0.0,
                "max_execution_time": round(op_metrics["max_execution_time"], 3),
            }

        return metrics

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format.

        Args:
            seconds: Uptime in seconds

        Returns:
            Human-readable uptime string
        """
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if days > 0:
            return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(secs)}s"
        elif hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(secs)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(secs)}s"
        else:
            return f"{int(secs)}s"

    def _calculate_success_rate(self) -> float:
        """Calculate success rate percentage.

        Returns:
            Success rate as percentage (0.0-100.0)
        """
        if self._total_requests == 0:
            return 0.0
        return round((self._successful_requests / self._total_requests) * 100, 2)

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._operation_metrics.clear()
        self._start_time = time.time()

        self._logger.info("Metrics reset to zero")
