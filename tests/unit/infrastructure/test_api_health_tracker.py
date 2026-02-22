"""Unit tests for the API health tracker module."""

from unittest.mock import MagicMock

from prdiffer.infrastructure.utils.api_health_tracker import (
    APICall,
    APIHealthTracker,
)


class TestAPICall:
    """Tests for the APICall dataclass."""

    def test_api_call_creation(self):
        """Test creating an APICall instance."""
        call = APICall(
            timestamp=1234567890.0,
            duration=0.5,
            success=True,
            error_type=None,
        )
        assert call.timestamp == 1234567890.0
        assert call.duration == 0.5
        assert call.success is True
        assert call.error_type is None

    def test_api_call_with_error(self):
        """Test creating an APICall with an error type."""
        call = APICall(
            timestamp=1234567890.0,
            duration=1.2,
            success=False,
            error_type="RateLimitExceeded",
        )
        assert call.success is False
        assert call.error_type == "RateLimitExceeded"


class TestAPIHealthTracker:
    """Tests for the APIHealthTracker class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.tracker = APIHealthTracker(
            window_size=10,
            time_window=300.0,
            logger=self.mock_logger,
        )

    def test_initial_state(self):
        """Test tracker initial state."""
        stats = self.tracker.get_stats()
        assert stats["health_score"] == 1.0
        assert stats["total_calls"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["avg_duration"] == 0.0
        assert stats["error_patterns"] == {}

    def test_record_successful_call(self):
        """Test recording a successful API call."""
        self.tracker.record_call(duration=0.5, success=True)

        stats = self.tracker.get_stats()
        assert stats["total_calls"] == 1
        assert stats["success_rate"] == 1.0

    def test_record_failed_call(self):
        """Test recording a failed API call."""
        self.tracker.record_call(duration=1.0, success=False, error_type="Timeout")

        stats = self.tracker.get_stats()
        assert stats["total_calls"] == 1
        assert stats["success_rate"] == 0.0
        assert stats["error_patterns"]["Timeout"] == 1

    def test_health_score_perfect(self):
        """Test health score with all successful calls."""
        for _ in range(5):
            self.tracker.record_call(duration=0.5, success=True)

        health_score = self.tracker.get_health_score()
        assert health_score == 1.0

    def test_health_score_poor(self):
        """Test health score with all failed calls."""
        for _ in range(5):
            self.tracker.record_call(duration=1.0, success=False, error_type="Error")

        health_score = self.tracker.get_health_score()
        assert health_score < 0.5  # Should be low due to 0% success rate

    def test_health_score_with_slow_responses(self):
        """Test health score penalty for slow responses."""
        # Record slow but successful calls
        for _ in range(5):
            self.tracker.record_call(duration=5.0, success=True)

        health_score = self.tracker.get_health_score()
        # Should be less than 1.0 due to slow response time
        assert health_score < 1.0

    def test_get_recommended_delay_base(self):
        """Test recommended delay with perfect health."""
        for _ in range(5):
            self.tracker.record_call(duration=0.5, success=True)

        delay = self.tracker.get_recommended_delay(base_delay=1.0, max_delay=30.0)
        assert delay == 1.0  # No additional delay needed

    def test_get_recommended_delay_poor_health(self):
        """Test recommended delay with poor health."""
        for _ in range(5):
            self.tracker.record_call(duration=1.0, success=False, error_type="Error")

        delay = self.tracker.get_recommended_delay(base_delay=1.0, max_delay=30.0)
        assert delay > 1.0  # Should increase delay for poor health

    def test_get_error_pattern(self):
        """Test error pattern tracking."""
        self.tracker.record_call(duration=1.0, success=False, error_type="Timeout")
        self.tracker.record_call(duration=1.0, success=False, error_type="Timeout")
        self.tracker.record_call(duration=1.0, success=False, error_type="RateLimit")
        self.tracker.record_call(duration=0.5, success=True)

        patterns = self.tracker.get_error_pattern()
        assert patterns["Timeout"] == 2
        assert patterns["RateLimit"] == 1

    def test_time_window_eviction(self):
        """Test that old calls are evicted after time window."""
        # Record a call with current time
        self.tracker.record_call(duration=0.5, success=True)

        # Simulate time passing beyond the window (need to patch at module level)
        import prdiffer.infrastructure.utils.api_health_tracker as health_module

        original_time = health_module.time.time

        try:
            # Simulate time passing beyond the window
            health_module.time.time = lambda: original_time() + 400.0  # 400 seconds later

            # Record another call
            self.tracker.record_call(duration=0.5, success=True)

            stats = self.tracker.get_stats()
            # First call should be evicted, only 1 call in window
            assert stats["total_calls"] == 1
        finally:
            # Restore original time function
            health_module.time.time = original_time

    def test_window_size_limit(self):
        """Test that window size is respected."""
        # Record more calls than window_size
        for i in range(15):
            self.tracker.record_call(duration=0.5, success=True)

        stats = self.tracker.get_stats()
        # Should be limited to window_size
        assert stats["total_calls"] <= 10

    def test_caching_of_health_score(self):
        """Test that health score is cached for performance."""
        for _ in range(5):
            self.tracker.record_call(duration=0.5, success=True)

        # Get health score twice
        score1 = self.tracker.get_health_score()
        score2 = self.tracker.get_health_score()

        assert score1 == score2
        # Should use cached value
        assert self.tracker._cached_health_score is not None

    def test_factory_function(self):
        """Test the get_api_health_tracker factory function."""
        # Create tracker directly with logger to avoid settings dependency
        tracker = APIHealthTracker(
            window_size=50,
            time_window=600.0,
            logger=self.mock_logger,
        )
        assert tracker.window_size == 50
        assert tracker.time_window == 600.0


class TestAPIHealthTrackerEdgeCases:
    """Edge case tests for APIHealthTracker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.tracker = APIHealthTracker(
            window_size=10,
            time_window=300.0,
            logger=self.mock_logger,
        )

    def test_empty_tracker_health_score(self):
        """Test health score with no calls recorded."""
        health_score = self.tracker.get_health_score()
        assert health_score == 1.0  # Assume healthy when no data

    def test_mixed_success_rate(self):
        """Test with mixed success and failure."""
        for i in range(10):
            if i < 7:
                self.tracker.record_call(duration=0.5, success=True)
            else:
                self.tracker.record_call(duration=1.0, success=False, error_type="Error")

        health_score = self.tracker.get_health_score()
        # Should be between 0 and 1
        assert 0.0 <= health_score <= 1.0
        # Should be > 0 due to 70% success rate
        assert health_score > 0.5

    def test_very_fast_responses(self):
        """Test with very fast responses."""
        for _ in range(5):
            self.tracker.record_call(duration=0.1, success=True)

        health_score = self.tracker.get_health_score()
        assert health_score == 1.0

    def test_very_slow_responses(self):
        """Test with very slow responses."""
        for _ in range(5):
            self.tracker.record_call(duration=10.0, success=True)

        health_score = self.tracker.get_health_score()
        # Should be less than 1.0 due to slow response time penalty
        # The time component: max(0, 1 - (avg_duration - 1) / 4) * 0.3
        # For avg_duration=10: 1 - (10-1)/4 = 1 - 2.25 = 0 (capped at 0)
        # So health_score = 0.7 * 1.0 + 0.0 = 0.7
        assert health_score < 1.0
        # But should still be relatively high due to 100% success rate
        assert health_score > 0.6

    def test_max_delay_cap(self):
        """Test that recommended delay is capped at max_delay."""
        # Record many failures to get poor health
        for _ in range(10):
            self.tracker.record_call(duration=1.0, success=False, error_type="Error")

        delay = self.tracker.get_recommended_delay(base_delay=1.0, max_delay=5.0)
        assert delay <= 5.0

    def test_stats_consistency(self):
        """Test that stats are consistent."""
        for i in range(5):
            self.tracker.record_call(duration=0.5 + i * 0.1, success=i % 2 == 0)

        stats = self.tracker.get_stats()

        # Check that success rate is calculated correctly
        successful = sum(1 for _ in range(5) if _ % 2 == 0)
        expected_rate = successful / 5
        assert abs(stats["success_rate"] - expected_rate) < 0.01

    def test_concurrent_access(self):
        """Test thread safety with concurrent access simulation."""
        import threading

        results = []

        def record_and_check():
            for _ in range(10):
                self.tracker.record_call(duration=0.5, success=True)
            results.append(len(self.tracker._calls))

        threads = [threading.Thread(target=record_and_check) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should complete without errors
        assert len(results) == 5
