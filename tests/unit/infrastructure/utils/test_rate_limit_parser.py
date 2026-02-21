"""Comprehensive tests for rate_limit_parser module."""

import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from prdiffer.infrastructure.utils.rate_limit_parser import (
    RateLimitInfo,
    get_error_headers,
    parse_int_header,
    parse_retry_after,
    extract_rate_limit_info,
    calculate_rate_limit_delay,
    is_rate_limit_remaining_below_threshold,
)


class TestRateLimitInfo:
    """Tests for RateLimitInfo dataclass."""

    def test_rate_limit_info_creation(self):
        """Test RateLimitInfo creation."""
        info = RateLimitInfo(
            remaining=100,
            limit=5000,
            reset_at=1234567890,
            retry_after=60.0,
        )

        assert info.remaining == 100
        assert info.limit == 5000
        assert info.reset_at == 1234567890
        assert info.retry_after == 60.0

    def test_rate_limit_info_frozen(self):
        """Test RateLimitInfo is frozen."""
        info = RateLimitInfo(
            remaining=100,
            limit=5000,
            reset_at=None,
            retry_after=None,
        )

        assert info.remaining == 100

    def test_rate_limit_info_with_none_values(self):
        """Test RateLimitInfo with None values."""
        info = RateLimitInfo(
            remaining=None,
            limit=None,
            reset_at=None,
            retry_after=None,
        )

        assert info.remaining is None
        assert info.limit is None
        assert info.reset_at is None
        assert info.retry_after is None


class TestGetErrorHeaders:
    """Tests for get_error_headers function."""

    def test_error_with_headers(self):
        """Test error with headers attribute."""
        error = MagicMock()
        error.headers = {'X-RateLimit-Remaining': '100'}

        result = get_error_headers(error)

        assert result == {'X-RateLimit-Remaining': '100'}

    def test_error_with_response_headers(self):
        """Test error with response.headers attribute."""
        error = MagicMock()
        del error.headers
        response = MagicMock()
        response.headers = {'X-RateLimit-Limit': '5000'}
        error.response = response

        result = get_error_headers(error)

        assert result == {'X-RateLimit-Limit': '5000'}

    def test_error_without_headers(self):
        """Test error without headers."""
        error = MagicMock()
        del error.headers
        error.response = None

        result = get_error_headers(error)

        assert result is None

    def test_error_headers_iteration_fails(self):
        """Test when headers iteration fails."""
        error = MagicMock()

        class BadHeaders:
            def items(self):
                raise Exception('Not iterable')

        error.headers = BadHeaders()

        result = get_error_headers(error)

        assert result is None


class TestParseIntHeader:
    """Tests for parse_int_header function."""

    def test_parse_valid_int(self):
        """Test parsing valid integer header."""
        headers = {'X-RateLimit-Remaining': '100'}

        result = parse_int_header(headers, 'X-RateLimit-Remaining')

        assert result == 100

    def test_parse_case_insensitive(self):
        """Test case insensitive header matching."""
        headers = {'x-ratelimit-remaining': '100'}

        result = parse_int_header(headers, 'X-RATELIMIT-REMAINING')

        assert result == 100

    def test_parse_missing_header(self):
        """Test missing header."""
        headers = {'Other-Header': 'value'}

        result = parse_int_header(headers, 'X-RateLimit-Remaining')

        assert result is None

    def test_parse_invalid_int(self):
        """Test invalid integer value."""
        headers = {'X-RateLimit-Remaining': 'not-a-number'}

        result = parse_int_header(headers, 'X-RateLimit-Remaining')

        assert result is None

    def test_parse_none_value(self):
        """Test None value in header."""
        headers = {'X-RateLimit-Remaining': None}

        result = parse_int_header(headers, 'X-RateLimit-Remaining')

        assert result is None


class TestParseRetryAfter:
    """Tests for parse_retry_after function."""

    def test_parse_seconds(self):
        """Test parsing seconds value."""
        headers = {'Retry-After': '60'}

        result = parse_retry_after(headers)

        assert result == 60.0

    def test_parse_case_insensitive(self):
        """Test case insensitive header matching."""
        headers = {'retry-after': '30'}

        result = parse_retry_after(headers)

        assert result == 30.0

    def test_parse_missing_header(self):
        """Test missing header."""
        headers = {'Other-Header': 'value'}

        result = parse_retry_after(headers)

        assert result is None

    def test_parse_invalid_number(self):
        """Test invalid number value."""
        headers = {'Retry-After': 'not-a-number'}

        result = parse_retry_after(headers)

        assert result is None

    def test_parse_http_date(self):
        """Test parsing HTTP date value."""
        future_time = datetime.now(timezone.utc) + timedelta(seconds=120)
        http_date = future_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
        headers = {'Retry-After': http_date}

        result = parse_retry_after(headers)

        assert result is not None
        assert 100 < result < 150

    def test_parse_negative_value(self):
        """Test negative value returns 0."""
        headers = {'Retry-After': '-10'}

        result = parse_retry_after(headers)

        assert result == 0.0

    def test_parse_float_value(self):
        """Test float value."""
        headers = {'Retry-After': '45.5'}

        result = parse_retry_after(headers)

        assert result == 45.5


class TestExtractRateLimitInfo:
    """Tests for extract_rate_limit_info function."""

    def test_extract_all_headers(self):
        """Test extracting all rate limit headers."""
        error = MagicMock()
        error.headers = {
            'X-RateLimit-Remaining': '100',
            'X-RateLimit-Limit': '5000',
            'X-RateLimit-Reset': '1234567890',
            'Retry-After': '60',
        }

        result = extract_rate_limit_info(error)

        assert result is not None
        assert result.remaining == 100
        assert result.limit == 5000
        assert result.reset_at == 1234567890
        assert result.retry_after == 60.0

    def test_extract_partial_headers(self):
        """Test extracting partial rate limit headers."""
        error = MagicMock()
        error.headers = {
            'X-RateLimit-Remaining': '100',
        }

        result = extract_rate_limit_info(error)

        assert result is not None
        assert result.remaining == 100
        assert result.limit is None
        assert result.reset_at is None
        assert result.retry_after is None

    def test_extract_no_headers(self):
        """Test extracting with no headers."""
        error = MagicMock()
        del error.headers

        result = extract_rate_limit_info(error)

        assert result is None

    def test_extract_empty_headers(self):
        """Test extracting with empty headers."""
        error = MagicMock()
        error.headers = {}

        result = extract_rate_limit_info(error)

        assert result is None


class TestCalculateRateLimitDelay:
    """Tests for calculate_rate_limit_delay function."""

    def test_delay_with_retry_after(self):
        """Test delay with retry_after."""
        info = RateLimitInfo(
            remaining=None,
            limit=None,
            reset_at=None,
            retry_after=60.0,
        )

        result = calculate_rate_limit_delay(info)

        assert result == 60.0

    def test_delay_with_reset_at(self):
        """Test delay with reset_at."""
        future_time = int(time.time()) + 120
        info = RateLimitInfo(
            remaining=None,
            limit=None,
            reset_at=future_time,
            retry_after=None,
        )

        result = calculate_rate_limit_delay(info)

        assert result is not None
        assert 100 < result < 130

    def test_delay_with_reset_buffer(self):
        """Test delay with reset buffer."""
        future_time = int(time.time()) + 60
        info = RateLimitInfo(
            remaining=None,
            limit=None,
            reset_at=future_time,
            retry_after=None,
        )

        result = calculate_rate_limit_delay(info, reset_buffer=10.0)

        assert result is not None
        assert 60 < result < 80

    def test_delay_none_info(self):
        """Test delay with None info."""
        result = calculate_rate_limit_delay(None)

        assert result is None

    def test_delay_negative_delay(self):
        """Test delay clamped to 0."""
        past_time = int(time.time()) - 60
        info = RateLimitInfo(
            remaining=None,
            limit=None,
            reset_at=past_time,
            retry_after=None,
        )

        result = calculate_rate_limit_delay(info)

        assert result == 0.0

    def test_delay_retry_after_takes_precedence(self):
        """Test retry_after takes precedence over reset_at."""
        future_time = int(time.time()) + 120
        info = RateLimitInfo(
            remaining=None,
            limit=None,
            reset_at=future_time,
            retry_after=30.0,
        )

        result = calculate_rate_limit_delay(info)

        assert result == 30.0


class TestIsRateLimitRemainingBelowThreshold:
    """Tests for is_rate_limit_remaining_below_threshold function."""

    def test_below_threshold(self):
        """Test remaining below threshold."""
        info = RateLimitInfo(
            remaining=0,
            limit=5000,
            reset_at=None,
            retry_after=None,
        )

        result = is_rate_limit_remaining_below_threshold(info, threshold=1)

        assert result is True

    def test_above_threshold(self):
        """Test remaining above threshold."""
        info = RateLimitInfo(
            remaining=100,
            limit=5000,
            reset_at=None,
            retry_after=None,
        )

        result = is_rate_limit_remaining_below_threshold(info, threshold=1)

        assert result is False

    def test_at_threshold(self):
        """Test remaining at threshold."""
        info = RateLimitInfo(
            remaining=1,
            limit=5000,
            reset_at=None,
            retry_after=None,
        )

        result = is_rate_limit_remaining_below_threshold(info, threshold=1)

        assert result is True

    def test_none_info(self):
        """Test with None info."""
        result = is_rate_limit_remaining_below_threshold(None)

        assert result is False

    def test_none_remaining(self):
        """Test with None remaining."""
        info = RateLimitInfo(
            remaining=None,
            limit=5000,
            reset_at=None,
            retry_after=None,
        )

        result = is_rate_limit_remaining_below_threshold(info)

        assert result is False

    def test_custom_threshold(self):
        """Test with custom threshold."""
        info = RateLimitInfo(
            remaining=5,
            limit=5000,
            reset_at=None,
            retry_after=None,
        )

        assert is_rate_limit_remaining_below_threshold(info, threshold=10) is True
        assert is_rate_limit_remaining_below_threshold(info, threshold=3) is False
