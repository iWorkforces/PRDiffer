"""Metrics tracking component for request statistics and monitoring."""

import time
import logging
import threading
from typing import Any
from prdiffer.domain.interfaces.protocols import MetricsTrackerProtocol
from prdiffer.domain.services.logger import LoggerServiceInterface


class MetricsTracker(MetricsTrackerProtocol):
    """Component responsible for tracking metrics and request statistics."""

    def __init__(self, logger: logging.Logger | LoggerServiceInterface | None = None):
        self._logger = logger or logging.getLogger(__name__)

        self._lock = threading.Lock()

        self._request_counter = 0

        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._start_time = time.time()

        self._operation_metrics: dict[str, dict[str, Any]] = {}

    def track_request(self, operation: str, success: bool, execution_time: float) -> None:
        with self._lock:
            self._total_requests += 1

            if success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1

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
            op_metrics["min_execution_time"] = min(op_metrics["min_execution_time"], execution_time)
            op_metrics["max_execution_time"] = max(op_metrics["max_execution_time"], execution_time)

            total_requests = self._total_requests

        self._logger.debug(
            f"Request tracked - operation: {operation}, success: {success}, execution_time: {execution_time:.3f}s, total_requests: {total_requests}"
        )

    def generate_request_id(self) -> str:
        with self._lock:
            self._request_counter += 1
            counter = self._request_counter
        return f"REQ-{int(time.time() * 1000)}-{counter}"

    def get_metrics_summary(self) -> dict[str, Any]:
        current_time = time.time()

        with self._lock:
            uptime_seconds = current_time - self._start_time
            total_requests = self._total_requests
            successful_requests = self._successful_requests
            failed_requests = self._failed_requests
            operation_metrics_copy: dict[str, dict[str, Any]] = {}
            for op, metrics in self._operation_metrics.items():
                operation_metrics_copy[op] = metrics.copy()

        operations_data: dict[str, dict[str, Any]] = {}

        for operation, op_metrics in operation_metrics_copy.items():
            avg_execution_time = 0.0
            if op_metrics["total_requests"] > 0:
                avg_execution_time = op_metrics["total_execution_time"] / op_metrics["total_requests"]

            success_rate = 0.0
            if op_metrics["total_requests"] > 0:
                success_rate = (op_metrics["successful_requests"] / op_metrics["total_requests"]) * 100

            operations_data[operation] = {
                "total_requests": op_metrics["total_requests"],
                "successful_requests": op_metrics["successful_requests"],
                "failed_requests": op_metrics["failed_requests"],
                "success_rate": round(success_rate, 2),
                "avg_execution_time": round(avg_execution_time, 3),
                "min_execution_time": round(op_metrics["min_execution_time"], 3) if op_metrics["min_execution_time"] != float("inf") else 0.0,
                "max_execution_time": round(op_metrics["max_execution_time"], 3),
            }

        metrics: dict[str, Any] = {
            "uptime_seconds": uptime_seconds,
            "uptime_human": self._format_uptime(uptime_seconds),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": self._calculate_success_rate_safe(successful_requests, total_requests),
            "operations": operations_data,
        }

        return metrics

    def _format_uptime(self, seconds: float) -> str:
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

    def _calculate_success_rate_safe(self, successful_requests: int, total_requests: int) -> float:
        if total_requests == 0:
            return 0.0
        return round((successful_requests / total_requests) * 100, 2)

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        with self._lock:
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._operation_metrics.clear()
            self._start_time = time.time()

        self._logger.info("Metrics reset to zero")
