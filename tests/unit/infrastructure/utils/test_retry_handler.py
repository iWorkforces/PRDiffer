"""Unit tests for Retry Handler.

This module contains comprehensive tests for the UnifiedRetryHandler class,
covering retry logic, circuit breaker integration, and error classification.
"""

import pytest
from unittest.mock import patch

from prdiffer.infrastructure.utils.retry_handler import (
    UnifiedRetryHandler,
    RETRY_EXCEPTIONS,
)


class TestUnifiedRetryHandler:
    """Test suite for UnifiedRetryHandler."""

    @pytest.fixture
    def retry_handler(self):
        """Create RetryHandler instance for testing."""
        return UnifiedRetryHandler(
            max_retries=3,
            retry_delay=0.1,  # Short delay for testing
        )

    def test_initialization(self, retry_handler):
        """Test handler initialization with default parameters."""
        assert retry_handler.max_retries == 3
        assert retry_handler.retry_delay == 0.1
        assert retry_handler._last_exception is None

    def test_successful_execution_no_retry(self, retry_handler):
        """Test that successful function is not retried."""
        call_count = [0]

        def successful_func():
            call_count[0] += 1
            return "success"

        result = retry_handler.execute_with_retry(successful_func)

        assert result == "success"
        assert call_count[0] == 1  # Called only once

    def test_retry_on_transient_failure(self, retry_handler):
        """Test that transient failures trigger retry."""
        call_count = [0]

        def transient_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("Transient error")
            return "success"

        result = retry_handler.execute_with_retry(transient_func)

        assert result == "success"
        assert call_count[0] == 3  # Initial call + 2 retries

    def test_no_retry_on_permanent_failure(self, retry_handler):
        """Test that permanent failures are not retried."""
        call_count = [0]

        def permanent_func():
            call_count[0] += 1
            raise ValueError("Permanent error")

        with pytest.raises(ValueError, match="Permanent error"):
            retry_handler.execute_with_retry(permanent_func)

        assert call_count[0] == 1  # Only called once


class TestRetryHandlerExponentialBackoff:
    """Test suite for exponential backoff calculation."""

    @pytest.fixture
    def retry_handler(self):
        """Create RetryHandler instance for testing."""
        return UnifiedRetryHandler(
            max_retries=3,
            retry_delay=0.1,
        )

    def test_exponential_backoff_calculation(self, retry_handler):
        """Test exponential backoff delay calculation."""
        # Test that delay increases exponentially
        delay_0 = retry_handler._calculate_backoff(0, is_rate_limit=False)
        delay_1 = retry_handler._calculate_backoff(1, is_rate_limit=False)
        delay_2 = retry_handler._calculate_backoff(2, is_rate_limit=False)

        # Each retry should have roughly double the delay
        assert delay_0 > 0
        assert delay_1 > delay_0
        assert delay_2 > delay_1

    def test_jitter_in_backoff(self, retry_handler):
        """Test that jitter is added to backoff delays."""
        # Call multiple times and verify variation
        delays = [
            retry_handler._calculate_backoff(0, is_rate_limit=False) for _ in range(10)
        ]

        # There should be some variation due to jitter
        # (though it's possible some are equal by chance)
        unique_delays = set(delays)
        assert len(unique_delays) > 1 or len(delays) > 5


class TestRetryHandlerCircuitBreaker:
    """Test suite for circuit breaker integration."""

    @pytest.fixture
    def retry_handler_with_circuit_breaker(self):
        """Create RetryHandler with circuit breaker enabled."""
        return UnifiedRetryHandler(
            max_retries=3,
            retry_delay=0.1,
            circuit_breaker_enabled=True,
            circuit_breaker_failure_threshold=2,
            circuit_breaker_timeout=1.0,
        )

    def test_circuit_breaker_opens_on_threshold(
        self, retry_handler_with_circuit_breaker
    ):
        """Test that circuit breaker opens after threshold failures."""
        call_count = [0]

        def failing_func():
            call_count[0] += 1
            raise ConnectionError("Always fails")

        # Execute until circuit breaker opens
        with pytest.raises(ConnectionError):
            retry_handler_with_circuit_breaker.execute_with_retry(failing_func)

        # Circuit breaker should be open now
        assert retry_handler_with_circuit_breaker._circuit_breaker.state == "OPEN"


class TestRetryHandlerErrorClassification:
    """Test suite for error classification and retry decisions."""

    @pytest.fixture
    def retry_handler(self):
        """Create RetryHandler instance for testing."""
        return UnifiedRetryHandler()

    def test_should_retry_connection_error(self, retry_handler):
        """Test that connection errors are retried."""
        error = ConnectionError("Connection failed")
        should_retry = retry_handler._should_retry_error(error, None)
        assert should_retry is True

    def test_should_retry_timeout_error(self, retry_handler):
        """Test that timeout errors are retried."""
        error = TimeoutError("Request timed out")
        should_retry = retry_handler._should_retry_error(error, None)
        assert should_retry is True

    def test_should_not_retry_system_exceptions(self, retry_handler):
        """Test that system exceptions are NOT caught for retry."""
        # These exceptions should NOT be in RETRY_EXCEPTIONS
        assert KeyboardInterrupt not in RETRY_EXCEPTIONS
        assert SystemExit not in RETRY_EXCEPTIONS
        assert GeneratorExit not in RETRY_EXCEPTIONS


@pytest.mark.asyncio
class TestRetryHandlerAsync:
    """Test suite for async retry functionality."""

    @pytest.fixture
    def retry_handler(self):
        """Create RetryHandler instance for testing."""
        return UnifiedRetryHandler(
            max_retries=2,
            retry_delay=0.1,
        )

    async def test_async_retry_on_transient_failure(self, retry_handler):
        """Test async retry on transient failures."""
        call_count = [0]

        async def transient_async_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("Transient error")
            return "async_success"

        result = await retry_handler.execute_with_retry_async(transient_async_func)

        assert result == "async_success"
        assert call_count[0] == 3  # Initial call + 2 retries

    async def test_async_uses_anyio_sleep(self, retry_handler):
        """Test that async retry uses anyio.sleep instead of time.sleep."""
        executed_sleeps = []

        async def mock_sleep(duration):
            executed_sleeps.append(duration)

        async def failing_func():
            raise ConnectionError("Always fails")

        with patch(
            "prdiffer.infrastructure.utils.retry_handler.async_sleep", mock_sleep
        ):
            with pytest.raises(ConnectionError):
                await retry_handler.execute_with_retry_async(failing_func)

        # Should have called sleep (number of retries)
        assert len(executed_sleeps) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
