"""Comprehensive tests for delay_calculator.py."""

import time
from unittest.mock import Mock, patch

from prdiffer.infrastructure.utils.delay_calculator import (
    calculate_basic_backoff,
    calculate_adaptive_delay,
    calculate_secondary_rate_limit_backoff,
    calculate_retry_delay,
)
from prdiffer.infrastructure.utils.rate_limit_parser import RateLimitInfo


class TestCalculateBasicBackoff:
    """Tests for calculate_basic_backoff function."""

    def test_first_attempt_base_delay(self):
        """Test that first attempt uses base delay."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay = calculate_basic_backoff(0, 1.0)

        assert delay == 1.0

    def test_exponential_growth(self):
        """Test exponential backoff growth."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay_0 = calculate_basic_backoff(0, 1.0)
            delay_1 = calculate_basic_backoff(1, 1.0)
            delay_2 = calculate_basic_backoff(2, 1.0)

        assert delay_0 == 1.0
        assert delay_1 == 2.0
        assert delay_2 == 4.0

    def test_jitter_added(self):
        """Test that jitter is added."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0.1
            delay = calculate_basic_backoff(0, 1.0)

        assert delay == 1.1

    def test_rate_limit_doubles_delay(self):
        """Test that rate limit errors double the delay."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay = calculate_basic_backoff(0, 1.0, is_rate_limit=True)

        assert delay == 2.0


class TestCalculateAdaptiveDelay:
    """Tests for calculate_adaptive_delay function."""

    def test_uses_health_tracker(self):
        """Test that health tracker is used when available."""
        mock_tracker = Mock()
        mock_tracker.get_recommended_delay.return_value = 5.0

        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay = calculate_adaptive_delay(0, 1.0, 2.0, health_tracker=mock_tracker)

        assert delay == 5.0
        mock_tracker.get_recommended_delay.assert_called()

    def test_rate_limit_error_doubles_delay(self):
        """Test that rate limit errors double delay when no health tracker."""
        error = Exception("403 rate limit")

        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            with patch(
                "prdiffer.infrastructure.utils.delay_calculator.is_rate_limit_error",
                return_value=True,
            ):
                delay = calculate_adaptive_delay(0, 1.0, 2.0, error=error)

        assert delay == 2.0

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        error = Exception("403 rate limit")

        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 100
            with patch(
                "prdiffer.infrastructure.utils.delay_calculator.is_rate_limit_error",
                return_value=True,
            ):
                delay = calculate_adaptive_delay(
                    0, 1.0, 2.0, error=error, max_delay=5.0
                )

        assert delay == 5.0

    def test_basic_delay_without_tracker(self):
        """Test basic delay without health tracker."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0.1
            delay = calculate_adaptive_delay(0, 1.0, 2.0)

        assert delay == 1.1


class TestCalculateSecondaryRateLimitBackoff:
    """Tests for calculate_secondary_rate_limit_backoff function."""

    def test_default_base_backoff(self):
        """Test default base backoff of 60 seconds."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay = calculate_secondary_rate_limit_backoff(0)

        assert delay == 60.0

    def test_exponential_growth(self):
        """Test exponential growth of secondary rate limit backoff."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay_0 = calculate_secondary_rate_limit_backoff(0)
            delay_1 = calculate_secondary_rate_limit_backoff(1)

        assert delay_0 == 60.0
        assert delay_1 == 120.0

    def test_custom_base_backoff(self):
        """Test custom base backoff."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay = calculate_secondary_rate_limit_backoff(0, base_backoff=30.0)

        assert delay == 30.0

    def test_jitter_added(self):
        """Test that jitter is added."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 6.0
            delay = calculate_secondary_rate_limit_backoff(0)

        assert delay == 66.0


class TestCalculateRetryDelay:
    """Tests for calculate_retry_delay function."""

    def test_retry_after_header_used(self):
        """Test that retry-after header is used."""
        rate_limit_info = RateLimitInfo(
            remaining=100,
            limit=5000,
            reset_at=None,
            retry_after=30,
        )

        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay = calculate_retry_delay(
                0,
                Exception("test"),
                1.0,
                2.0,
                rate_limit_info=rate_limit_info,
            )

        assert delay == 30

    def test_reset_at_header_used(self):
        """Test that reset_at header is used."""
        future_time = time.time() + 120
        rate_limit_info = RateLimitInfo(
            remaining=100,
            limit=5000,
            reset_at=int(future_time),
            retry_after=None,
        )

        delay = calculate_retry_delay(
            0,
            Exception("test"),
            1.0,
            2.0,
            rate_limit_info=rate_limit_info,
            reset_buffer=1.0,
        )

        assert 120 < delay < 122

    def test_secondary_rate_limit_backoff(self):
        """Test secondary rate limit uses special backoff."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay = calculate_retry_delay(
                0,
                Exception("test"),
                1.0,
                2.0,
                is_secondary_rate_limit=True,
                secondary_backoff=60.0,
            )

        assert delay == 60.0

    def test_secondary_rate_limit_with_header_max(self):
        """Test secondary rate limit takes max of backoff and header."""
        rate_limit_info = RateLimitInfo(
            remaining=100,
            limit=5000,
            reset_at=None,
            retry_after=120,
        )

        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay = calculate_retry_delay(
                0,
                Exception("test"),
                1.0,
                2.0,
                rate_limit_info=rate_limit_info,
                is_secondary_rate_limit=True,
                secondary_backoff=60.0,
            )

        assert delay == 120

    def test_adaptive_delay_enabled(self):
        """Test adaptive delay when enabled."""
        mock_tracker = Mock()
        mock_tracker.get_recommended_delay.return_value = 10.0

        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay = calculate_retry_delay(
                0,
                Exception("test"),
                1.0,
                2.0,
                use_adaptive=True,
                health_tracker=mock_tracker,
            )

        assert delay == 10.0

    def test_basic_backoff_fallback(self):
        """Test basic backoff as fallback."""
        with patch(
            "prdiffer.infrastructure.utils.delay_calculator.random"
        ) as mock_random:
            mock_random.uniform.return_value = 0
            delay = calculate_retry_delay(
                0,
                Exception("test"),
                1.0,
                2.0,
            )

        assert delay == 1.0

    def test_header_delay_takes_priority(self):
        """Test that header delay takes priority over other calculations."""
        rate_limit_info = RateLimitInfo(
            remaining=100,
            limit=5000,
            reset_at=None,
            retry_after=45,
        )

        delay = calculate_retry_delay(
            0,
            Exception("test"),
            1.0,
            2.0,
            rate_limit_info=rate_limit_info,
            use_adaptive=True,
        )

        assert delay == 45

    def test_negative_reset_delay_clamped(self):
        """Test that negative reset delay is clamped to 0."""
        past_time = time.time() - 100
        rate_limit_info = RateLimitInfo(
            remaining=100,
            limit=5000,
            reset_at=int(past_time),
            retry_after=None,
        )

        delay = calculate_retry_delay(
            0,
            Exception("test"),
            1.0,
            2.0,
            rate_limit_info=rate_limit_info,
            reset_buffer=1.0,
        )

        assert delay >= 0
