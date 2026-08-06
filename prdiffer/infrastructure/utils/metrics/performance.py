"""Performance metrics collection and tracking."""

import time
import threading
from typing import TypedDict
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class MetricValue:
    count: int = 0
    total: float = 0.0
    min_val: float = float("inf")
    max_val: float = float("-inf")

    def update(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)

    @property
    def average(self) -> float:
        return self.total / self.count if self.count > 0 else 0.0


class MetricSnapshot(TypedDict):
    count: int
    total: float
    average: float
    min: float
    max: float


class PerformanceSummary(TypedDict):
    cache_hit_rate: float
    cache_total_requests: int
    feature_flag_adoption_rate: float


class PerformanceMetricsSnapshot(TypedDict):
    uptime_seconds: float
    uptime_human: str
    counters: dict[str, int]
    metrics: dict[str, MetricSnapshot]
    summary: PerformanceSummary


class PerformanceMetrics:
    """Thread-safe performance metrics collector."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counters: dict[str, int] = defaultdict(int)
        self._metrics: dict[str, MetricValue] = defaultdict(MetricValue)
        self._start_time = time.time()

    def increment_counter(self, name: str, delta: int = 1) -> None:
        with self._lock:
            self._counters[name] += delta

    def record_metric(self, name: str, value: float) -> None:
        with self._lock:
            self._metrics[name].update(value)

    def record_latency(self, operation: str, duration_seconds: float) -> None:
        self.record_metric(f"latency.{operation}", duration_seconds)

    def get_counter(self, name: str) -> int:
        with self._lock:
            return self._counters.get(name, 0)

    def get_metric(self, name: str) -> MetricSnapshot:
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

    def get_all_metrics(self) -> PerformanceMetricsSnapshot:
        with self._lock:
            uptime = time.time() - self._start_time

            cache_hits = self._counters.get("cache.hits", 0)
            cache_misses = self._counters.get("cache.misses", 0)
            total_cache_requests = cache_hits + cache_misses
            cache_hit_rate = (cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0.0

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
        """Format uptime in human-readable format (e.g., "2h 30m 15s")."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts: list[str] = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._metrics.clear()
            self._start_time = time.time()


_metrics_instance: PerformanceMetrics | None = None
_metrics_lock = threading.Lock()


def get_performance_metrics() -> PerformanceMetrics:
    """Get or create the global PerformanceMetrics singleton."""
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                _metrics_instance = PerformanceMetrics()
    return _metrics_instance
