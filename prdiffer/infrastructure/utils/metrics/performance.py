"""Performance metrics collection and tracking.

Tracks cache performance, feature flag adoption, API calls, and latency.
"""

import time
import time
import threading
from typing import Any
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricValue:
    """Container for a single metric value."""

    count: int = 0
    total: float = 0.0
    min_val: float = float("inf")
    max_val: float = float("-inf")

    def update(self, value: float) -> None:
        """Update metric with new value."""
        self.count += 1
        self.total += value
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)

    @property
    def average(self) -> float:
        """Calculate average value."""
        return self.total / self.count if self.count > 0 else 0.0


class PerformanceMetrics:
    """Thread-safe performance metrics collector.

    Tracks:
    - Cache hit/miss rates
    - Feature flag adoption rates
    - API call counts
    - Latency percentiles (simplified)
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._lock = threading.RLock()
        self._counters: dict[str, int] = defaultdict(int)
        self._metrics: dict[str, MetricValue] = defaultdict(MetricValue)
        self._start_time = time.time()

    def increment_counter(self, name: str, delta: int = 1) -> None:
        """Increment a counter metric.

        Args:
            name: Counter name
            delta: Value to increment by (default: 1)
        """
        with self._lock:
            self._counters[name] += delta

    def record_metric(self, name: str, value: float) -> None:
        """Record a value metric (for averages, min/max).

        Args:
            name: Metric name
            value: Value to record
        """
        with self._lock:
            self._metrics[name].update(value)

    def record_latency(self, operation: str, duration_seconds: float) -> None:
        """Record operation latency.

        Args:
            operation: Operation name
            duration_seconds: Duration in seconds
        """
        self.record_metric(f"latency.{operation}", duration_seconds)

    def get_counter(self, name: str) -> int:
        """Get counter value.

        Args:
            name: Counter name

        Returns:
            Current counter value
        """
        with self._lock:
            return self._counters.get(name, 0)

    def get_metric(self, name: str) -> dict[str, Any]:
        """Get metric statistics.

        Args:
            name: Metric name

        Returns:
            Dictionary with count, total, average, min, max
        """
        with self._lock:
            metric = self._metrics.get(name)
            if metric is None or metric.count == 0:
                return {
                    "count": 0,
                    "total": 0.0,
                    "average": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                }
            return {
                "count": metric.count,
                "total": metric.total,
                "average": metric.average,
                "min": metric.min_val if metric.min_val != float("inf") else 0.0,
                "max": metric.max_val if metric.max_val != float("-inf") else 0.0,
            }

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics and counters.

        Returns:
            Dictionary with all metrics, counters, and metadata
        """
        with self._lock:
            uptime = time.time() - self._start_time

            # Calculate rates
            cache_hits = self._counters.get("cache.hits", 0)
            cache_misses = self._counters.get("cache.misses", 0)
            total_cache_requests = cache_hits + cache_misses
            cache_hit_rate = (cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0.0

            # Feature flag adoption
            ff_enabled = self._counters.get("feature_flags.enabled", 0)
            ff_total = self._counters.get("feature_flags.total", 0)
            ff_adoption_rate = (ff_enabled / ff_total * 100) if ff_total > 0 else 0.0

            return {
                "uptime_seconds": uptime,
                "uptime_human": self._format_uptime(uptime),
                "counters": dict(self._counters),
                "metrics": {name: self.get_metric(name) for name in self._metrics.keys()},
                "summary": {
                    "cache_hit_rate": cache_hit_rate,
                    "cache_total_requests": total_cache_requests,
                    "feature_flag_adoption_rate": ff_adoption_rate,
                },
            }

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format.

        Args:
            seconds: Uptime in seconds

        Returns:
            Human-readable string (e.g., "2h 30m 15s")
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._metrics.clear()
            self._start_time = time.time()


# Global metrics instance
_metrics_instance: PerformanceMetrics | None = None
_metrics_lock = threading.Lock()


def get_performance_metrics() -> PerformanceMetrics:
    """Get global performance metrics instance.

    Returns:
        PerformanceMetrics: Global instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                _metrics_instance = PerformanceMetrics()
    return _metrics_instance
