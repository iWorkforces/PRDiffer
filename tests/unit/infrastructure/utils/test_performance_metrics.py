import pytest

from prdiffer.infrastructure.utils import performance as compatibility_performance
from prdiffer.infrastructure.utils.metrics import performance as canonical_performance


@pytest.mark.unit
def test_compatibility_import_uses_canonical_metric_singleton() -> None:
    # Given: both supported performance metric import paths
    # When: each path resolves its global metric collector
    compatibility_metrics = compatibility_performance.get_performance_metrics()
    canonical_metrics = canonical_performance.get_performance_metrics()

    # Then: both paths expose the same implementation and singleton state
    assert compatibility_performance.PerformanceMetrics is canonical_performance.PerformanceMetrics
    assert compatibility_metrics is canonical_metrics


@pytest.mark.unit
def test_metric_snapshot_preserves_public_keys_and_values() -> None:
    # Given: a metrics collector with counters and a recorded latency metric
    metrics = canonical_performance.PerformanceMetrics()
    metrics.increment_counter("cache.hits", 2)
    metrics.increment_counter("cache.misses")
    metrics.increment_counter("feature_flags.enabled", 3)
    metrics.increment_counter("feature_flags.total", 4)
    metrics.record_latency("fetch", 1.25)
    metrics.record_latency("fetch", 2.75)

    # When: callers request its public snapshot
    snapshot = metrics.get_all_metrics()

    # Then: the established snapshot keys and values remain unchanged
    assert set(snapshot) == {"uptime_seconds", "uptime_human", "counters", "metrics", "summary"}
    assert snapshot["counters"] == {
        "cache.hits": 2,
        "cache.misses": 1,
        "feature_flags.enabled": 3,
        "feature_flags.total": 4,
    }
    assert snapshot["metrics"] == {
        "latency.fetch": {"count": 2, "total": 4.0, "average": 2.0, "min": 1.25, "max": 2.75}
    }
    assert snapshot["summary"] == {
        "cache_hit_rate": 66.66666666666666,
        "cache_total_requests": 3,
        "feature_flag_adoption_rate": 75.0,
    }
