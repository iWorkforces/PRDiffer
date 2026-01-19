"""Unit tests for MetricsTracker application component.

Tests the MetricsTracker component which provides thread-safe
request metrics collection and reporting.
"""

import time
import threading
import pytest
from unittest.mock import Mock
from prdiffer.application.components.metrics_tracker import MetricsTracker


class TestMetricsTrackerInitialization:
    """Test suite for MetricsTracker initialization."""

    def test_metrics_tracker_initialization(self):
        """Test MetricsTracker can be initialized."""
        tracker = MetricsTracker()

        assert tracker is not None
        assert hasattr(tracker, "_total_requests")
        assert hasattr(tracker, "_successful_requests")
        assert hasattr(tracker, "_failed_requests")
        assert hasattr(tracker, "_operation_metrics")

    def test_metrics_tracker_with_logger(self):
        """Test MetricsTracker with custom logger."""
        mock_logger = Mock()
        tracker = MetricsTracker(logger=mock_logger)

        assert tracker._logger == mock_logger

    def test_metrics_tracker_initial_state(self):
        """Test MetricsTracker starts with zero metrics."""
        tracker = MetricsTracker()

        assert tracker._total_requests == 0
        assert tracker._successful_requests == 0
        assert tracker._failed_requests == 0
        assert len(tracker._operation_metrics) == 0

    def test_metrics_tracker_has_lock(self):
        """Test MetricsTracker has thread safety lock."""
        tracker = MetricsTracker()

        assert hasattr(tracker, "_lock")
        assert isinstance(tracker._lock, type(threading.Lock()))


class TestMetricsTrackerTrackRequest:
    """Test suite for track_request method."""

    def test_track_request_success(self):
        """Test tracking a successful request."""
        tracker = MetricsTracker()

        tracker.track_request("test_operation", success=True, execution_time=0.5)

        assert tracker._total_requests == 1
        assert tracker._successful_requests == 1
        assert tracker._failed_requests == 0

    def test_track_request_failure(self):
        """Test tracking a failed request."""
        tracker = MetricsTracker()

        tracker.track_request("test_operation", success=False, execution_time=0.3)

        assert tracker._total_requests == 1
        assert tracker._successful_requests == 0
        assert tracker._failed_requests == 1

    def test_track_request_multiple(self):
        """Test tracking multiple requests."""
        tracker = MetricsTracker()

        tracker.track_request("op1", success=True, execution_time=0.1)
        tracker.track_request("op1", success=False, execution_time=0.2)
        tracker.track_request("op2", success=True, execution_time=0.3)

        assert tracker._total_requests == 3
        assert tracker._successful_requests == 2
        assert tracker._failed_requests == 1

    def test_track_request_operation_metrics(self):
        """Test that operation-specific metrics are tracked."""
        tracker = MetricsTracker()

        tracker.track_request("get_pr_diff", success=True, execution_time=1.0)
        tracker.track_request("get_pr_diff", success=False, execution_time=0.5)

        op_metrics = tracker._operation_metrics.get("get_pr_diff")

        assert op_metrics is not None
        assert op_metrics["total_requests"] == 2
        assert op_metrics["successful_requests"] == 1
        assert op_metrics["failed_requests"] == 1
        assert op_metrics["total_execution_time"] == 1.5

    def test_track_request_execution_time_tracking(self):
        """Test execution time min/max/total tracking."""
        tracker = MetricsTracker()

        tracker.track_request("op", success=True, execution_time=0.1)
        tracker.track_request("op", success=True, execution_time=0.5)
        tracker.track_request("op", success=True, execution_time=0.3)

        op_metrics = tracker._operation_metrics.get("op")

        assert op_metrics["min_execution_time"] == 0.1
        assert op_metrics["max_execution_time"] == 0.5
        assert op_metrics["total_execution_time"] == pytest.approx(0.9)

    def test_track_request_new_operation_initializes_metrics(self):
        """Test that new operations initialize with zero values."""
        tracker = MetricsTracker()

        tracker.track_request("new_op", success=True, execution_time=0.25)

        op_metrics = tracker._operation_metrics.get("new_op")

        assert op_metrics["total_requests"] == 1
        assert op_metrics["successful_requests"] == 1
        assert op_metrics["failed_requests"] == 0
        assert op_metrics["total_execution_time"] == 0.25


class TestMetricsTrackerGenerateRequestId:
    """Test suite for generate_request_id method."""

    def test_generate_request_id_format(self):
        """Test request ID has correct format."""
        tracker = MetricsTracker()

        request_id = tracker.generate_request_id()

        assert request_id.startswith("REQ-")
        parts = request_id.split("-")
        assert len(parts) == 3

    def test_generate_request_id_unique(self):
        """Test that each request ID is unique."""
        tracker = MetricsTracker()

        ids = [tracker.generate_request_id() for _ in range(100)]

        assert len(set(ids)) == 100  # All unique

    def test_generate_request_id_counter_increments(self):
        """Test that request counter increments."""
        tracker = MetricsTracker()

        id1 = tracker.generate_request_id()
        id2 = tracker.generate_request_id()

        # Extract counters from IDs
        counter1 = int(id1.split("-")[-1])
        counter2 = int(id2.split("-")[-1])

        assert counter2 == counter1 + 1

    def test_generate_request_id_timestamp_included(self):
        """Test that timestamp is included in request ID."""
        tracker = MetricsTracker()
        before_time = int(time.time() * 1000)

        request_id = tracker.generate_request_id()

        after_time = int(time.time() * 1000)
        timestamp = int(request_id.split("-")[1])

        assert before_time <= timestamp <= after_time


class TestMetricsTrackerGetMetricsSummary:
    """Test suite for get_metrics_summary method."""

    def test_get_metrics_summary_initial(self):
        """Test metrics summary when no requests tracked."""
        tracker = MetricsTracker()

        summary = tracker.get_metrics_summary()

        assert summary["total_requests"] == 0
        assert summary["successful_requests"] == 0
        assert summary["failed_requests"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["uptime_seconds"] >= 0

    def test_get_metrics_summary_after_requests(self):
        """Test metrics summary after tracking requests."""
        tracker = MetricsTracker()

        tracker.track_request("op1", success=True, execution_time=0.1)
        tracker.track_request("op1", success=False, execution_time=0.2)

        summary = tracker.get_metrics_summary()

        assert summary["total_requests"] == 2
        assert summary["successful_requests"] == 1
        assert summary["failed_requests"] == 1
        assert summary["success_rate"] == 50.0

    def test_get_metrics_summary_includes_operations(self):
        """Test metrics summary includes operation-specific data."""
        tracker = MetricsTracker()

        tracker.track_request("op1", success=True, execution_time=0.1)
        tracker.track_request("op1", success=True, execution_time=0.3)

        summary = tracker.get_metrics_summary()

        assert "op1" in summary["operations"]
        op_data = summary["operations"]["op1"]
        assert op_data["total_requests"] == 2
        assert op_data["successful_requests"] == 2
        assert op_data["failed_requests"] == 0
        assert op_data["success_rate"] == 100.0

    def test_get_metrics_summary_avg_execution_time(self):
        """Test average execution time calculation."""
        tracker = MetricsTracker()

        tracker.track_request("op", success=True, execution_time=0.1)
        tracker.track_request("op", success=True, execution_time=0.3)
        tracker.track_request("op", success=True, execution_time=0.5)

        summary = tracker.get_metrics_summary()

        op_data = summary["operations"]["op"]
        assert op_data["avg_execution_time"] == 0.3

    def test_get_metrics_summary_min_max_execution_time(self):
        """Test min/max execution time tracking."""
        tracker = MetricsTracker()

        tracker.track_request("op", success=True, execution_time=0.1)
        tracker.track_request("op", success=True, execution_time=0.5)

        summary = tracker.get_metrics_summary()

        op_data = summary["operations"]["op"]
        assert op_data["min_execution_time"] == 0.1
        assert op_data["max_execution_time"] == 0.5

    def test_get_metrics_summary_uptime(self):
        """Test uptime calculation."""
        tracker = MetricsTracker()

        time.sleep(0.1)  # Small delay
        summary = tracker.get_metrics_summary()

        assert summary["uptime_seconds"] >= 0.1
        assert "uptime_human" in summary

    def test_get_metrics_summary_uptime_human_format(self):
        """Test human-readable uptime format."""
        tracker = MetricsTracker()

        summary = tracker.get_metrics_summary()
        uptime = summary["uptime_human"]

        # Should end with 's' for seconds
        assert uptime.endswith("s")


class TestMetricsTrackerUptimeFormatting:
    """Test suite for _format_uptime method."""

    def test_format_uptime_seconds(self):
        """Test formatting uptime in seconds."""
        tracker = MetricsTracker()

        assert tracker._format_uptime(30) == "30s"
        assert tracker._format_uptime(59) == "59s"

    def test_format_uptime_minutes(self):
        """Test formatting uptime with minutes."""
        tracker = MetricsTracker()

        assert tracker._format_uptime(60) == "1m 0s"
        assert tracker._format_uptime(90) == "1m 30s"
        assert tracker._format_uptime(3599) == "59m 59s"

    def test_format_uptime_hours(self):
        """Test formatting uptime with hours."""
        tracker = MetricsTracker()

        assert tracker._format_uptime(3600) == "1h 0m 0s"
        assert tracker._format_uptime(3661) == "1h 1m 1s"
        assert tracker._format_uptime(86399) == "23h 59m 59s"

    def test_format_uptime_days(self):
        """Test formatting uptime with days."""
        tracker = MetricsTracker()

        assert tracker._format_uptime(86400) == "1d 0h 0m 0s"
        assert tracker._format_uptime(90061) == "1d 1h 1m 1s"


class TestMetricsTrackerCalculateSuccessRate:
    """Test suite for _calculate_success_rate method."""

    def test_calculate_success_rate_no_requests(self):
        """Test success rate with no requests."""
        tracker = MetricsTracker()

        rate = tracker._calculate_success_rate()

        assert rate == 0.0

    def test_calculate_success_rate_all_success(self):
        """Test success rate with all successful requests."""
        tracker = MetricsTracker()

        tracker.track_request("op", success=True, execution_time=0.1)
        tracker.track_request("op", success=True, execution_time=0.1)

        rate = tracker._calculate_success_rate()

        assert rate == 100.0

    def test_calculate_success_rate_half_success(self):
        """Test success rate with mixed results."""
        tracker = MetricsTracker()

        tracker.track_request("op", success=True, execution_time=0.1)
        tracker.track_request("op", success=False, execution_time=0.1)

        rate = tracker._calculate_success_rate()

        assert rate == 50.0

    def test_calculate_success_rate_safe_no_requests(self):
        """Test safe success rate calculation with no requests."""
        tracker = MetricsTracker()

        rate = tracker._calculate_success_rate_safe(0, 0)

        assert rate == 0.0

    def test_calculate_success_rate_safe_all_success(self):
        """Test safe success rate calculation."""
        tracker = MetricsTracker()

        rate = tracker._calculate_success_rate_safe(10, 10)

        assert rate == 100.0

    def test_calculate_success_rate_safe_half_success(self):
        """Test safe success rate calculation with mixed results."""
        tracker = MetricsTracker()

        rate = tracker._calculate_success_rate_safe(5, 10)

        assert rate == 50.0


class TestMetricsTrackerResetMetrics:
    """Test suite for reset_metrics method."""

    def test_reset_metrics_clears_all(self):
        """Test that reset clears all metrics."""
        tracker = MetricsTracker()

        tracker.track_request("op1", success=True, execution_time=0.1)
        tracker.track_request("op2", success=False, execution_time=0.2)

        tracker.reset_metrics()

        assert tracker._total_requests == 0
        assert tracker._successful_requests == 0
        assert tracker._failed_requests == 0
        assert len(tracker._operation_metrics) == 0

    def test_reset_metrics_resets_start_time(self):
        """Test that reset clears start time."""
        tracker = MetricsTracker()

        time.sleep(0.1)
        old_start = tracker._start_time

        tracker.reset_metrics()

        assert tracker._start_time > old_start

    def test_reset_metrics_summary_after_reset(self):
        """Test metrics summary after reset."""
        tracker = MetricsTracker()

        tracker.track_request("op", success=True, execution_time=0.1)
        tracker.reset_metrics()

        summary = tracker.get_metrics_summary()

        assert summary["total_requests"] == 0
        assert summary["successful_requests"] == 0
        assert summary["failed_requests"] == 0


class TestMetricsTrackerThreadSafety:
    """Test suite for thread safety."""

    def test_track_request_thread_safe(self):
        """Test that track_request is thread-safe."""
        tracker = MetricsTracker()
        num_threads = 10
        requests_per_thread = 100

        def track_requests():
            for i in range(requests_per_thread):
                tracker.track_request(
                    f"op_{i % 5}", success=i % 2 == 0, execution_time=0.1
                )

        threads = [threading.Thread(target=track_requests) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected_total = num_threads * requests_per_thread
        assert tracker._total_requests == expected_total

    def test_generate_request_id_thread_safe(self):
        """Test that generate_request_id is thread-safe."""
        tracker = MetricsTracker()
        num_threads = 10
        ids_per_thread = 100

        ids = []
        lock = threading.Lock()

        def generate_ids():
            thread_ids = []
            for _ in range(ids_per_thread):
                thread_ids.append(tracker.generate_request_id())
            with lock:
                ids.extend(thread_ids)

        threads = [threading.Thread(target=generate_ids) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All IDs should be unique
        assert len(set(ids)) == num_threads * ids_per_thread

    def test_get_metrics_summary_thread_safe(self):
        """Test that get_metrics_summary doesn't block tracking."""
        tracker = MetricsTracker()
        results = []

        def continuous_tracking():
            for i in range(100):
                tracker.track_request("op", success=True, execution_time=0.01)

        def continuous_reading():
            for _ in range(50):
                summary = tracker.get_metrics_summary()
                results.append(summary["total_requests"])

        t1 = threading.Thread(target=continuous_tracking)
        t2 = threading.Thread(target=continuous_reading)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Should have completed without deadlock
        assert len(results) == 50
        assert tracker._total_requests == 100


class TestMetricsTrackerEdgeCases:
    """Test suite for edge cases."""

    def test_zero_execution_time(self):
        """Test handling of zero execution time."""
        tracker = MetricsTracker()

        tracker.track_request("op", success=True, execution_time=0.0)

        summary = tracker.get_metrics_summary()
        op_data = summary["operations"]["op"]

        assert op_data["min_execution_time"] == 0.0
        assert op_data["max_execution_time"] == 0.0

    def test_very_small_execution_time(self):
        """Test handling of very small execution time."""
        tracker = MetricsTracker()

        tracker.track_request("op", success=True, execution_time=0.0001)

        summary = tracker.get_metrics_summary()
        op_data = summary["operations"]["op"]

        assert op_data["min_execution_time"] == 0.0  # Rounded
        assert op_data["max_execution_time"] == 0.0

    def test_large_execution_time(self):
        """Test handling of large execution time."""
        tracker = MetricsTracker()

        tracker.track_request("op", success=True, execution_time=1000.5)

        summary = tracker.get_metrics_summary()
        op_data = summary["operations"]["op"]

        assert op_data["max_execution_time"] == 1000.5

    def test_empty_operation_name(self):
        """Test handling of empty operation name."""
        tracker = MetricsTracker()

        tracker.track_request("", success=True, execution_time=0.1)

        summary = tracker.get_metrics_summary()

        assert "" in summary["operations"]

    def test_special_characters_in_operation_name(self):
        """Test handling of special characters in operation name."""
        tracker = MetricsTracker()

        tracker.track_request("op/test-123", success=True, execution_time=0.1)

        summary = tracker.get_metrics_summary()

        assert "op/test-123" in summary["operations"]

    def test_negative_execution_time(self):
        """Test handling of negative execution time."""
        tracker = MetricsTracker()

        # This shouldn't happen in practice, but test graceful handling
        tracker.track_request("op", success=True, execution_time=-0.1)

        summary = tracker.get_metrics_summary()
        op_data = summary["operations"]["op"]

        # Should track even if negative
        assert op_data["min_execution_time"] == -0.1


class TestMetricsTrackerProtocolCompliance:
    """Test suite for MetricsTracker protocol compliance."""

    def test_has_required_methods(self):
        """Test that MetricsTracker has all required protocol methods."""
        tracker = MetricsTracker()

        # Check all required methods exist
        assert hasattr(tracker, "track_request")
        assert callable(tracker.track_request)
        assert hasattr(tracker, "get_metrics_summary")
        assert callable(tracker.get_metrics_summary)
        assert hasattr(tracker, "generate_request_id")
        assert callable(tracker.generate_request_id)
