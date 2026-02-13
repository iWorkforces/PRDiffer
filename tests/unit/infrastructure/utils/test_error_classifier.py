"""Comprehensive tests for error_classifier module."""


from prdiffer.infrastructure.utils.error_classifier import (
    PERMANENT_ERROR_CODES,
    SERVER_ERROR_CODES,
    TRANSIENT_ERROR_PATTERNS,
    SECONDARY_RATE_LIMIT_PATTERNS,
    is_permanent_error,
    is_server_error,
    is_transient_error,
    is_secondary_rate_limit_error,
    get_error_message,
    categorize_error,
    should_retry_by_error_code,
    is_rate_limit_error,
    RetryDecision,
    classify_error_for_retry,
)


class TestErrorCodes:
    """Tests for error code sets."""

    def test_permanent_error_codes(self):
        """Test permanent error codes set."""
        assert "404" in PERMANENT_ERROR_CODES
        assert "401" in PERMANENT_ERROR_CODES
        assert "403" in PERMANENT_ERROR_CODES
        assert "500" not in PERMANENT_ERROR_CODES

    def test_server_error_codes(self):
        """Test server error codes set."""
        assert "500" in SERVER_ERROR_CODES
        assert "502" in SERVER_ERROR_CODES
        assert "503" in SERVER_ERROR_CODES
        assert "504" in SERVER_ERROR_CODES
        assert "404" not in SERVER_ERROR_CODES

    def test_transient_error_patterns(self):
        """Test transient error patterns."""
        assert "timeout" in TRANSIENT_ERROR_PATTERNS
        assert "connection" in TRANSIENT_ERROR_PATTERNS
        assert "network" in TRANSIENT_ERROR_PATTERNS

    def test_secondary_rate_limit_patterns(self):
        """Test secondary rate limit patterns."""
        assert "secondary rate limit" in SECONDARY_RATE_LIMIT_PATTERNS
        assert "abuse detection" in SECONDARY_RATE_LIMIT_PATTERNS


class TestIsPermanentError:
    """Tests for is_permanent_error function."""

    def test_permanent_errors(self):
        """Test permanent error codes."""
        assert is_permanent_error("404") is True
        assert is_permanent_error("401") is True
        assert is_permanent_error("403") is True

    def test_non_permanent_errors(self):
        """Test non-permanent error codes."""
        assert is_permanent_error("500") is False
        assert is_permanent_error("503") is False
        assert is_permanent_error("200") is False


class TestIsServerError:
    """Tests for is_server_error function."""

    def test_server_errors(self):
        """Test server error codes."""
        assert is_server_error("500") is True
        assert is_server_error("502") is True
        assert is_server_error("503") is True
        assert is_server_error("504") is True

    def test_non_server_errors(self):
        """Test non-server error codes."""
        assert is_server_error("404") is False
        assert is_server_error("403") is False
        assert is_server_error("200") is False


class TestIsTransientError:
    """Tests for is_transient_error function."""

    def test_transient_timeout(self):
        """Test transient timeout error."""
        assert is_transient_error("Connection timeout") is True

    def test_transient_connection(self):
        """Test transient connection error."""
        assert is_transient_error("Connection refused") is True

    def test_transient_network(self):
        """Test transient network error."""
        assert is_transient_error("Network error") is True

    def test_transient_502(self):
        """Test transient 502 error."""
        assert is_transient_error("Error 502 Bad Gateway") is True

    def test_non_transient(self):
        """Test non-transient error."""
        assert is_transient_error("File not found") is False
        assert is_transient_error("Authentication failed") is False

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        assert is_transient_error("TIMEOUT ERROR") is True
        assert is_transient_error("Connection TIMEOUT") is True


class TestIsSecondaryRateLimitError:
    """Tests for is_secondary_rate_limit_error function."""

    def test_secondary_rate_limit(self):
        """Test secondary rate limit error."""
        error = Exception("secondary rate limit exceeded")
        assert is_secondary_rate_limit_error(error) is True

    def test_abuse_detection(self):
        """Test abuse detection error."""
        error = Exception("abuse detection mechanism triggered")
        assert is_secondary_rate_limit_error(error) is True

    def test_api_abuse(self):
        """Test API abuse error."""
        error = Exception("api abuse detected")
        assert is_secondary_rate_limit_error(error) is True

    def test_temporarily_blocked(self):
        """Test temporarily blocked error."""
        error = Exception("temporarily blocked for abuse")
        assert is_secondary_rate_limit_error(error) is True

    def test_regular_error(self):
        """Test regular error is not secondary rate limit."""
        error = Exception("Not found")
        assert is_secondary_rate_limit_error(error) is False

    def test_error_with_data_dict(self):
        """Test error with data dict attribute."""
        error = Exception("Rate limit")
        error.data = {"message": "secondary rate limit"}
        assert is_secondary_rate_limit_error(error) is True

    def test_error_with_data_string(self):
        """Test error with data string attribute."""
        error = Exception("Error")
        error.data = "secondary rate limit exceeded"
        assert is_secondary_rate_limit_error(error) is True


class TestGetErrorMessage:
    """Tests for get_error_message function."""

    def test_simple_error(self):
        """Test simple error message."""
        error = Exception("Test error")
        result = get_error_message(error)

        assert "test error" in result

    def test_error_with_data_dict(self):
        """Test error with data dict."""
        error = Exception("Base error")
        error.data = {"message": "Data message"}
        result = get_error_message(error)

        assert "base error" in result
        assert "data message" in result

    def test_error_with_data_string(self):
        """Test error with data string."""
        error = Exception("Base error")
        error.data = "Additional info"
        result = get_error_message(error)

        assert "base error" in result
        assert "additional info" in result

    def test_error_without_data(self):
        """Test error without data attribute."""
        error = Exception("Simple error")
        result = get_error_message(error)

        assert result == "simple error"


class TestCategorizeError:
    """Tests for categorize_error function."""

    def test_not_found(self):
        """Test 404 categorization."""
        error = Exception("404 Not Found")
        assert categorize_error(error) == "not_found"

    def test_authentication_403(self):
        """Test 403 categorization."""
        error = Exception("403 Forbidden")
        assert categorize_error(error) == "authentication"

    def test_authentication_401(self):
        """Test 401 categorization."""
        error = Exception("401 Unauthorized")
        assert categorize_error(error) == "authentication"

    def test_rate_limit(self):
        """Test rate limit categorization."""
        error = Exception("429 Too Many Requests")
        assert categorize_error(error) == "rate_limit"

        error2 = Exception("Rate limit exceeded")
        assert categorize_error(error2) == "rate_limit"

    def test_server_error_500(self):
        """Test 500 categorization."""
        error = Exception("500 Internal Server Error")
        assert categorize_error(error) == "server_error"

    def test_server_error_503(self):
        """Test 503 categorization."""
        error = Exception("503 Service Unavailable")
        assert categorize_error(error) == "server_error"

    def test_timeout(self):
        """Test timeout categorization."""
        error = Exception("Request timeout")
        assert categorize_error(error) == "timeout"

    def test_network(self):
        """Test network categorization."""
        error = Exception("Connection failed")
        assert categorize_error(error) == "network"

        error2 = Exception("Network unreachable")
        assert categorize_error(error2) == "network"

    def test_unknown(self):
        """Test unknown categorization."""
        error = Exception("Something went wrong")
        assert categorize_error(error) == "unknown"


class TestShouldRetryByErrorCode:
    """Tests for should_retry_by_error_code function."""

    def test_retry_404_enabled(self):
        """Test retry on 404 when enabled."""
        assert should_retry_by_error_code("404 Not Found", True, True, True) is True

    def test_retry_404_disabled(self):
        """Test no retry on 404 when disabled."""
        assert should_retry_by_error_code("404 Not Found", False, True, True) is False

    def test_retry_403_enabled(self):
        """Test retry on 403 when enabled."""
        assert should_retry_by_error_code("403 Forbidden", True, True, True) is True

    def test_retry_403_disabled(self):
        """Test no retry on 403 when disabled."""
        assert should_retry_by_error_code("403 Forbidden", True, False, True) is False

    def test_retry_500_enabled(self):
        """Test retry on 500 when enabled."""
        assert should_retry_by_error_code("500 Error", True, True, True) is True

    def test_retry_500_disabled(self):
        """Test no retry on 500 when disabled."""
        assert should_retry_by_error_code("500 Error", True, True, False) is False

    def test_retry_other_error(self):
        """Test retry on other error."""
        assert should_retry_by_error_code("Timeout", True, True, True) is True


class TestIsRateLimitError:
    """Tests for is_rate_limit_error function."""

    def test_rate_limit_429(self):
        """Test 429 rate limit error."""
        error = Exception("429 Too Many Requests")
        assert is_rate_limit_error(error) is True

    def test_rate_limit_message(self):
        """Test rate limit message."""
        error = Exception("Rate limit exceeded")
        assert is_rate_limit_error(error) is True

    def test_secondary_rate_limit(self):
        """Test secondary rate limit error."""
        error = Exception("secondary rate limit")
        assert is_rate_limit_error(error) is True

    def test_non_rate_limit(self):
        """Test non-rate limit error."""
        error = Exception("Not found")
        assert is_rate_limit_error(error) is False


class TestRetryDecision:
    """Tests for RetryDecision dataclass."""

    def test_retry_decision_creation(self):
        """Test RetryDecision creation."""
        decision = RetryDecision(
            should_retry=True,
            reason="Test reason",
            is_rate_limit=True,
            is_permanent=False,
        )

        assert decision.should_retry is True
        assert decision.reason == "Test reason"
        assert decision.is_rate_limit is True
        assert decision.is_permanent is False

    def test_retry_decision_mutable(self):
        """Test RetryDecision is mutable."""
        decision = RetryDecision(
            should_retry=True,
            reason="Test",
            is_rate_limit=False,
            is_permanent=False,
        )

        decision.should_retry = False
        assert decision.should_retry is False


class TestClassifyErrorForRetry:
    """Tests for classify_error_for_retry function."""

    def test_classify_404_no_retry(self):
        """Test 404 with retry disabled."""
        error = Exception("404 Not Found")
        decision = classify_error_for_retry(error, retry_on_404=False)

        assert decision.should_retry is False
        assert decision.is_permanent is True

    def test_classify_404_retry(self):
        """Test 404 with retry enabled."""
        error = Exception("404 Not Found")
        decision = classify_error_for_retry(error, retry_on_404=True)

        assert decision.should_retry is False

    def test_classify_403_no_retry(self):
        """Test 403 with retry disabled."""
        error = Exception("403 Forbidden")
        decision = classify_error_for_retry(error, retry_on_403=False)

        assert decision.should_retry is False
        assert decision.is_permanent is True

    def test_classify_500_no_retry(self):
        """Test 500 with retry disabled."""
        error = Exception("500 Internal Server Error")
        decision = classify_error_for_retry(error, retry_on_500=False)

        assert decision.should_retry is False
        assert decision.is_permanent is True

    def test_classify_transient_retry(self):
        """Test transient error should retry."""
        error = Exception("Connection timeout")
        decision = classify_error_for_retry(error)

        assert decision.should_retry is True
        assert decision.is_rate_limit is False
        assert decision.is_permanent is False

    def test_classify_rate_limit_retry(self):
        """Test rate limit error should retry."""
        error = Exception("429 Rate limit exceeded")
        decision = classify_error_for_retry(error)

        assert decision.should_retry is True
        assert decision.is_rate_limit is True

    def test_classify_unknown_no_retry(self):
        """Test unknown error should not retry."""
        error = Exception("Unknown error")
        decision = classify_error_for_retry(error)

        assert decision.should_retry is False
        assert decision.is_permanent is True

    def test_classify_defaults(self):
        """Test default parameters."""
        error = Exception("Test error")
        decision = classify_error_for_retry(error)

        assert isinstance(decision, RetryDecision)
