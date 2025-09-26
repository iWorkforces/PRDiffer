"""Retry handler utility for GitHub API operations with exponential backoff."""

import time
import random
from typing import Any, Callable
from ccpragents.domain.services import RetryServiceInterface
from ccpragents.infrastructure.logging.console_logger import get_logger


class RetryHandler(RetryServiceInterface):
    """Handler for retrying operations with exponential backoff and jitter.

    This utility provides configurable retry logic for GitHub API operations
    with smart error classification and context-aware retry strategies.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_on_404: bool = False,
        retry_on_403: bool = True,
        retry_on_500: bool = True,
        retry_log_level: str = "DEBUG",
        permanent_failure_log_level: str = "INFO",
        logger=None,
    ):
        """Initialize the retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            retry_on_404: Whether to retry 404 (Not Found) errors
            retry_on_403: Whether to retry 403 (Forbidden) errors
            retry_on_500: Whether to retry 5xx server errors
            retry_log_level: Log level for retry attempts (DEBUG, INFO, WARNING)
            permanent_failure_log_level: Log level for permanent failures
            logger: Logger instance for logging retry attempts
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_on_404 = retry_on_404
        self.retry_on_403 = retry_on_403
        self.retry_on_500 = retry_on_500
        self.retry_log_level = retry_log_level.upper()
        self.permanent_failure_log_level = permanent_failure_log_level.upper()
        self._logger = logger or get_logger()

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with retry logic and exponential backoff.

        Args:
            func: Function to execute with retry logic
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the successful function call

        Raises:
            Exception: If all retry attempts fail or error is not retryable
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if this error should be retried
                should_retry = self._should_retry_error(e)
                is_last_attempt = attempt == self.max_retries - 1

                if not should_retry or is_last_attempt:
                    # Log permanent failure or final attempt
                    self._log_permanent_failure(e, should_retry, is_last_attempt)
                    raise

                # Calculate backoff with jitter
                delay = self._calculate_backoff(attempt, self._is_rate_limit_error(e))

                # Log the retry attempt
                self._log_retry_attempt(attempt, delay, e)

                time.sleep(delay)

        # This should not be reached, but just in case
        if last_exception:
            raise last_exception

    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error should be retried based on configuration.

        Args:
            error: Exception to check

        Returns:
            bool: True if this error should be retried, False otherwise
        """
        error_str = str(error).lower()

        # Check for 404 errors
        if "404" in error_str and not self.retry_on_404:
            return False

        # Check for 403 errors (might be rate limiting or permissions)
        if "403" in error_str and not self.retry_on_403:
            return False

        # Check for 5xx server errors
        if (
            any(f"{code}" in error_str for code in [500, 501, 502, 503, 504])
            and not self.retry_on_500
        ):
            return False

        # Retry rate limit errors and other transient errors
        return (
            self._is_rate_limit_error(error)
            or "timeout" in error_str
            or "connection" in error_str
            or "network" in error_str
            or "503" in error_str  # Service unavailable
            or "502" in error_str  # Bad gateway
            or "504" in error_str  # Gateway timeout
        )

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an exception indicates a rate limit error.

        Args:
            error: Exception to check

        Returns:
            bool: True if this is a rate limit error, False otherwise
        """
        error_str = str(error).lower()
        return (
            "rate limit" in error_str or "429" in str(error)  # Too Many Requests
        )

    def _calculate_backoff(self, attempt: int, is_rate_limit: bool) -> float:
        """Calculate backoff delay with exponential growth and jitter.

        Args:
            attempt: Current attempt number (0-based)
            is_rate_limit: Whether this is a rate limit error

        Returns:
            float: Delay in seconds before next retry
        """
        base_delay = self.retry_delay * (2**attempt)
        jitter = random.uniform(0, base_delay * 0.1)  # 10% jitter
        return base_delay + jitter

    def _log_retry_attempt(self, attempt: int, delay: float, error: Exception):
        """Log retry attempt information at configured level.

        Args:
            attempt: Current attempt number (0-based)
            delay: Delay before next retry in seconds
            error: Exception that caused the retry
        """
        is_rate_limit = self._is_rate_limit_error(error)

        if is_rate_limit:
            message = (
                f"Rate limit hit, retrying in {delay:.2f}s "
                f"(attempt {attempt + 1}/{self.max_retries})"
            )
        else:
            # Truncate long error messages for cleaner logs
            error_msg = str(error)
            if len(error_msg) > 100:
                error_msg = error_msg[:97] + "..."
            message = (
                f"API error, retrying in {delay:.2f}s "
                f"(attempt {attempt + 1}/{self.max_retries}): {error_msg}"
            )

        # Log at configured level
        self._log_at_level(message, self.retry_log_level)

    def _log_permanent_failure(
        self, error: Exception, should_retry: bool, is_last_attempt: bool
    ):
        """Log permanent failure or final attempt information.

        Args:
            error: Exception that caused the failure
            should_retry: Whether this error type is configured for retry
            is_last_attempt: Whether this was the last retry attempt
        """
        if not should_retry:
            # Permanent failure due to error type
            error_msg = str(error)
            if len(error_msg) > 150:
                error_msg = error_msg[:147] + "..."
            message = f"Permanent failure (no retry configured): {error_msg}"
            self._log_at_level(message, self.permanent_failure_log_level)
        elif is_last_attempt:
            # Final attempt failed
            message = f"All retry attempts exhausted: {str(error)[:100]}..."
            self._log_at_level(message, "ERROR")

    def _log_at_level(self, message: str, level: str):
        """Log message at specified level.

        Args:
            message: Message to log
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level = level.upper()
        if level == "DEBUG":
            self._logger.debug(message)
        elif level == "INFO":
            self._logger.info(message)
        elif level == "WARNING":
            self._logger.warning(message)
        elif level == "ERROR":
            self._logger.error(message)
        elif level == "CRITICAL":
            self._logger.critical(message)
        else:
            # Fallback to INFO for unknown levels
            self._logger.info(message)


def get_retry_handler(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    retry_on_404: bool = False,
    retry_on_403: bool = True,
    retry_on_500: bool = True,
    retry_log_level: str = "DEBUG",
    permanent_failure_log_level: str = "INFO",
) -> RetryHandler:
    """Get a configured retry handler instance.

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds
        retry_on_404: Whether to retry 404 (Not Found) errors
        retry_on_403: Whether to retry 403 (Forbidden) errors
        retry_on_500: Whether to retry 5xx server errors
        retry_log_level: Log level for retry attempts
        permanent_failure_log_level: Log level for permanent failures

    Returns:
        RetryHandler: Configured retry handler instance
    """
    return RetryHandler(
        max_retries=max_retries,
        retry_delay=retry_delay,
        retry_on_404=retry_on_404,
        retry_on_403=retry_on_403,
        retry_on_500=retry_on_500,
        retry_log_level=retry_log_level,
        permanent_failure_log_level=permanent_failure_log_level,
    )
