"""Unified retry handler utility for GitHub API operations with optional advanced features.

This module provides a unified retry handler that combines basic retry logic with
optional advanced features like circuit breaker, health tracking, and context-aware strategies.
It replaces both the basic RetryHandler and AdvancedRetryHandler with a single configurable class.

The handler supports both synchronous and asynchronous operations:
- execute_with_retry(): Synchronous version using time.sleep()
- execute_with_retry_async(): Async version using anyio.sleep() (non-blocking)
"""

import time
import random
import threading
from typing import Any, Callable, Optional, Dict, Coroutine, TypeVar

import anyio

from enum import StrEnum
from prdiffer.domain.services import RetryServiceInterface


T = TypeVar("T")


class OperationContext(StrEnum):
    """Context types for different operations."""

    REPOSITORY_ACCESS = "repository_access"
    FILE_CONTENT = "file_content"
    PULL_REQUEST = "pull_request"
    BATCH_OPERATION = "batch_operation"


class UnifiedRetryHandler(RetryServiceInterface):
    """Unified handler for retrying operations with optional advanced features.

    This utility provides configurable retry logic for GitHub API operations
    with optional features like circuit breaker, health tracking, and context-aware strategies.
    It combines the functionality of both basic and advanced retry handlers into a single class.

    Features:
    - Basic exponential backoff with jitter (always enabled)
    - Optional circuit breaker pattern for cascading failure prevention
    - Optional API health tracking for adaptive retry delays
    - Optional context-aware retry strategies
    - Smart error classification and retry decisions
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
        # Advanced features (optional)
        use_advanced_features: bool = False,
        circuit_breaker_enabled: bool = False,
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_timeout: float = 60.0,
        adaptive_retry_enabled: bool = False,
        max_adaptive_delay: float = 30.0,
        api_health_tracking: bool = False,
        context_aware_retry: bool = False,
        logger=None,
    ):
        """Initialize the unified retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            retry_on_404: Whether to retry 404 (Not Found) errors
            retry_on_403: Whether to retry 403 (Forbidden) errors
            retry_on_500: Whether to retry 5xx server errors
            retry_log_level: Log level for retry attempts (DEBUG, INFO, WARNING)
            permanent_failure_log_level: Log level for permanent failures
            use_advanced_features: Enable all advanced features at once
            circuit_breaker_enabled: Enable circuit breaker pattern
            circuit_breaker_failure_threshold: Failures before opening circuit
            circuit_breaker_timeout: Seconds to keep circuit open
            adaptive_retry_enabled: Enable adaptive retry delays
            max_adaptive_delay: Maximum adaptive delay in seconds
            api_health_tracking: Enable API health tracking
            context_aware_retry: Enable context-aware retry strategies
            logger: Logger instance for logging retry attempts
        """
        # Basic retry configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_on_404 = retry_on_404
        self.retry_on_403 = retry_on_403
        self.retry_on_500 = retry_on_500
        self.retry_log_level = retry_log_level.upper()
        self.permanent_failure_log_level = permanent_failure_log_level.upper()

        # Logger is optional - if not provided, we'll get it lazily to avoid circular imports
        self._logger = logger
        self._logger_fetched = logger is not None
        self._logger_lock = threading.Lock()

        # Advanced features configuration
        self.use_advanced_features = use_advanced_features
        if use_advanced_features:
            # Enable all advanced features when use_advanced_features is True
            self.circuit_breaker_enabled = True
            self.adaptive_retry_enabled = True
            self.api_health_tracking = True
            self.context_aware_retry = True
        else:
            # Use individual feature flags
            self.circuit_breaker_enabled = circuit_breaker_enabled
            self.adaptive_retry_enabled = adaptive_retry_enabled
            self.api_health_tracking = api_health_tracking
            self.context_aware_retry = context_aware_retry

        self.max_adaptive_delay = max_adaptive_delay

        # Initialize advanced components if enabled
        self._circuit_breaker: Optional[Any] = None
        self._health_tracker: Optional[Any] = None

        if self.circuit_breaker_enabled:
            from prdiffer.infrastructure.utils.circuit_breaker import CircuitBreaker

            self._circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_failure_threshold,
                timeout=circuit_breaker_timeout,
                logger=self._get_logger(),
            )

        if self.api_health_tracking:
            from prdiffer.infrastructure.utils.api_health_tracker import (
                APIHealthTracker,
            )

            self._health_tracker = APIHealthTracker(logger=self._get_logger())

        # Context-specific retry configurations
        self._context_configs: Dict[OperationContext, Dict] = {}
        if self.context_aware_retry:
            self._context_configs = {
                OperationContext.REPOSITORY_ACCESS: {
                    "max_retries": max_retries,
                    "retry_delay": retry_delay * 2,  # Longer delays for repo access
                    "backoff_multiplier": 2.0,
                },
                OperationContext.FILE_CONTENT: {
                    "max_retries": max_retries - 1,  # Fewer retries for file content
                    "retry_delay": retry_delay,
                    "backoff_multiplier": 1.5,
                },
                OperationContext.PULL_REQUEST: {
                    "max_retries": max_retries + 1,  # More retries for PR data
                    "retry_delay": retry_delay,
                    "backoff_multiplier": 2.0,
                },
                OperationContext.BATCH_OPERATION: {
                    "max_retries": max_retries - 1,  # Fewer retries for batch ops
                    "retry_delay": retry_delay * 0.5,  # Shorter delays
                    "backoff_multiplier": 1.5,
                },
            }

    def execute_with_retry(
        self,
        func: Callable,
        *args,
        context: Optional[OperationContext] = None,
        **kwargs,
    ) -> Any:
        """Execute a function with retry logic and exponential backoff.

        Args:
            func: Function to execute with retry logic
            *args: Positional arguments for the function
            context: Optional operation context for context-aware retry (only used with advanced features)
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the successful function call

        Raises:
            Exception: If all retry attempts fail, error is not retryable, or circuit breaker is open
        """
        # Check circuit breaker if enabled
        if self._circuit_breaker and self.circuit_breaker_enabled:
            if not self._circuit_breaker.can_execute():
                from prdiffer.infrastructure.utils.circuit_breaker import (
                    CircuitBreakerOpenException,
                )

                raise CircuitBreakerOpenException(
                    f"Circuit breaker is open. State: {self._circuit_breaker.state.value}"
                )

        # Get context-specific configuration if context-aware retry is enabled
        config = self._get_context_config(context)
        max_retries = config["max_retries"]
        base_delay = config["retry_delay"]
        backoff_multiplier = config.get("backoff_multiplier", 2.0)

        last_exception = None
        start_time = time.time() if self._health_tracker else None

        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)

                # Record success if health tracking is enabled
                if self._health_tracker and start_time:
                    self._record_success(start_time)

                return result

            except Exception as e:
                last_exception = e

                # Record failure if health tracking is enabled
                if self._health_tracker:
                    self._record_failure(e)

                # Check if this error should be retried
                should_retry = self._should_retry_error(e, context)
                is_last_attempt = attempt == max_retries - 1

                if not should_retry or is_last_attempt:
                    # Log permanent failure or final attempt
                    self._log_permanent_failure(e, should_retry, is_last_attempt)
                    raise

                # Calculate delay (adaptive if enabled, basic otherwise)
                if self.adaptive_retry_enabled:
                    delay = self._calculate_adaptive_delay(
                        attempt, e, base_delay, backoff_multiplier
                    )
                else:
                    delay = self._calculate_backoff(
                        attempt, self._is_rate_limit_error(e)
                    )

                # Log the retry attempt
                self._log_retry_attempt(attempt, delay, e, context)

                time.sleep(delay)

        # This should not be reached, but just in case
        if last_exception:
            raise last_exception

    async def execute_with_retry_async(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args,
        context: Optional[OperationContext] = None,
        **kwargs,
    ) -> T:
        """Execute an async function with retry logic and exponential backoff (non-blocking).

        This is the async version of execute_with_retry(). It uses anyio.sleep() instead
        of time.sleep() to avoid blocking the event loop during retry delays.

        Args:
            func: Async function to execute with retry logic
            *args: Positional arguments for the function
            context: Optional operation context for context-aware retry (only used with advanced features)
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the successful function call

        Raises:
            Exception: If all retry attempts fail, error is not retryable, or circuit breaker is open
        """
        # Check circuit breaker if enabled
        if self._circuit_breaker and self.circuit_breaker_enabled:
            if not self._circuit_breaker.can_execute():
                from prdiffer.infrastructure.utils.circuit_breaker import (
                    CircuitBreakerOpenException,
                )

                raise CircuitBreakerOpenException(
                    f"Circuit breaker is open. State: {self._circuit_breaker.state.value}"
                )

        # Get context-specific configuration if context-aware retry is enabled
        config = self._get_context_config(context)
        max_retries = config["max_retries"]
        base_delay = config["retry_delay"]
        backoff_multiplier = config.get("backoff_multiplier", 2.0)

        last_exception: Optional[Exception] = None
        start_time = time.time() if self._health_tracker else None

        for attempt in range(max_retries):
            try:
                result = await func(*args, **kwargs)

                # Record success if health tracking is enabled
                if self._health_tracker and start_time:
                    self._record_success(start_time)

                return result

            except Exception as e:
                last_exception = e

                # Record failure if health tracking is enabled
                if self._health_tracker:
                    self._record_failure(e)

                # Check if this error should be retried
                should_retry = self._should_retry_error(e, context)
                is_last_attempt = attempt == max_retries - 1

                if not should_retry or is_last_attempt:
                    # Log permanent failure or final attempt
                    self._log_permanent_failure(e, should_retry, is_last_attempt)
                    raise

                # Calculate delay (adaptive if enabled, basic otherwise)
                if self.adaptive_retry_enabled:
                    delay = self._calculate_adaptive_delay(
                        attempt, e, base_delay, backoff_multiplier
                    )
                else:
                    delay = self._calculate_backoff(
                        attempt, self._is_rate_limit_error(e)
                    )

                # Log the retry attempt
                self._log_retry_attempt(attempt, delay, e, context)

                # Use anyio.sleep() for non-blocking delay (async-compatible)
                await anyio.sleep(delay)

        # This should not be reached, but just in case
        if last_exception:
            raise last_exception

        # Type checker requires a return, though this is unreachable
        raise RuntimeError("Unexpected state: no result and no exception")

    def _get_context_config(self, context: Optional[OperationContext]) -> Dict:
        """Get configuration for specific operation context.

        Args:
            context: Operation context

        Returns:
            dict: Context-specific configuration or default configuration
        """
        if context and self.context_aware_retry and context in self._context_configs:
            return self._context_configs[context]

        # Default configuration
        return {
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "backoff_multiplier": 2.0,
        }

    def _should_retry_error(
        self, error: Exception, context: Optional[OperationContext] = None
    ) -> bool:
        """Determine if an error should be retried based on configuration.

        Args:
            error: Exception to check
            context: Optional operation context for context-aware retry

        Returns:
            bool: True if this error should be retried, False otherwise
        """
        error_str = str(error).lower()

        # Basic error classification
        if "404" in error_str and not self.retry_on_404:
            return False
        if "403" in error_str and not self.retry_on_403:
            return False
        if (
            any(f"{code}" in error_str for code in [500, 501, 502, 503, 504])
            and not self.retry_on_500
        ):
            return False

        # Context-aware retry logic (only if enabled)
        if context and self.context_aware_retry:
            if context == OperationContext.FILE_CONTENT and "404" in error_str:
                # Never retry 404s for file content (likely added/removed files)
                return False
            elif context == OperationContext.REPOSITORY_ACCESS and "401" in error_str:
                # Don't retry authentication errors for repository access
                return False
            elif context == OperationContext.BATCH_OPERATION and "timeout" in error_str:
                # Be more aggressive with batch operation timeouts
                return True

        # Standard transient error detection
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
        """Calculate basic backoff delay with exponential growth and jitter.

        Args:
            attempt: Current attempt number (0-based)
            is_rate_limit: Whether this is a rate limit error

        Returns:
            float: Delay in seconds before next retry
        """
        base_delay: float = self.retry_delay * (2**attempt)
        jitter: float = random.uniform(0, base_delay * 0.1)  # 10% jitter
        return float(base_delay + jitter)

    def _calculate_adaptive_delay(
        self,
        attempt: int,
        error: Exception,
        base_delay: float,
        backoff_multiplier: float,
    ) -> float:
        """Calculate adaptive retry delay based on API health and error type.

        Args:
            attempt: Current attempt number (0-based)
            error: Exception that caused the retry
            base_delay: Base delay for this context
            backoff_multiplier: Backoff multiplier for this context

        Returns:
            float: Adaptive delay in seconds
        """
        # Basic exponential backoff
        exponential_delay = base_delay * (backoff_multiplier**attempt)

        # Add jitter
        jitter = random.uniform(0, exponential_delay * 0.1)
        delay_with_jitter = exponential_delay + jitter

        # Adaptive delay based on API health
        if self.adaptive_retry_enabled and self._health_tracker:
            adaptive_delay: float = self._health_tracker.get_recommended_delay(
                delay_with_jitter, self.max_adaptive_delay
            )
            return float(adaptive_delay)

        # Rate limit errors get longer delays
        if self._is_rate_limit_error(error):
            return min(delay_with_jitter * 2, self.max_adaptive_delay)

        return delay_with_jitter

    def _record_success(self, start_time: float):
        """Record a successful operation (only used with advanced features).

        Args:
            start_time: Start time of the operation
        """
        duration = time.time() - start_time

        if self._circuit_breaker:
            self._circuit_breaker.record_success()

        if self._health_tracker:
            self._health_tracker.record_call(duration, success=True)

    def _record_failure(self, error: Exception):
        """Record a failed operation (only used with advanced features).

        Args:
            error: Exception that occurred
        """
        if self._circuit_breaker:
            self._circuit_breaker.record_failure()

        if self._health_tracker:
            error_type = self._categorize_error(error)
            self._health_tracker.record_call(0.0, success=False, error_type=error_type)

    def _categorize_error(self, error: Exception) -> str:
        """Categorize error for health tracking.

        Args:
            error: Exception to categorize

        Returns:
            str: Error category
        """
        error_str = str(error).lower()

        if "404" in error_str:
            return "not_found"
        elif "403" in error_str or "401" in error_str:
            return "authentication"
        elif "429" in error_str or "rate limit" in error_str:
            return "rate_limit"
        elif any(f"{code}" in error_str for code in [500, 502, 503, 504]):
            return "server_error"
        elif "timeout" in error_str:
            return "timeout"
        elif "connection" in error_str or "network" in error_str:
            return "network"
        else:
            return "unknown"

    def _get_logger(self):
        """Get logger instance, lazily loading if needed to avoid circular imports.

        Uses double-checked locking pattern for thread safety.
        """
        if not self._logger_fetched:
            with self._logger_lock:
                # Double-check pattern to avoid race conditions
                if not self._logger_fetched:
                    from prdiffer.infrastructure.logging.console_logger import (
                        get_logger,
                    )

                    self._logger = get_logger()
                    self._logger_fetched = True
        return self._logger

    def _log_retry_attempt(
        self,
        attempt: int,
        delay: float,
        error: Exception,
        context: Optional[OperationContext] = None,
    ):
        """Log retry attempt information at configured level.

        Args:
            attempt: Current attempt number (0-based)
            delay: Delay before next retry in seconds
            error: Exception that caused the retry
            context: Optional operation context
        """
        is_rate_limit = self._is_rate_limit_error(error)
        context_str = (
            f" [{context.value}]" if context and self.context_aware_retry else ""
        )

        if is_rate_limit:
            message = (
                f"Rate limit hit{context_str}, retrying in {delay:.2f}s "
                f"(attempt {attempt + 1})"
            )
        else:
            # Truncate long error messages for cleaner logs
            error_msg = str(error)
            if len(error_msg) > 100:
                error_msg = error_msg[:97] + "..."
            message = (
                f"API error{context_str}, retrying in {delay:.2f}s "
                f"(attempt {attempt + 1}): {error_msg}"
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
        logger = self._get_logger()
        level = level.upper()
        if level == "DEBUG":
            logger.debug(message)
        elif level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
        elif level == "CRITICAL":
            logger.critical(message)
        else:
            # Fallback to INFO for unknown levels
            logger.info(message)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive retry handler statistics (only for advanced features).

        Returns:
            dict: Statistics including circuit breaker and health tracker info
        """
        stats: Dict[str, Any] = {
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            "adaptive_retry_enabled": self.adaptive_retry_enabled,
            "api_health_tracking": self.api_health_tracking,
            "context_aware_retry": self.context_aware_retry,
        }

        if self._circuit_breaker:
            stats["circuit_breaker"] = self._circuit_breaker.get_stats()

        if self._health_tracker:
            stats["api_health"] = self._health_tracker.get_stats()

        return stats


# Backward compatibility aliases
RetryHandler = UnifiedRetryHandler  # Alias for backward compatibility


def get_retry_handler(**kwargs) -> UnifiedRetryHandler:
    """Get a configured retry handler instance.

    This function creates a basic retry handler without advanced features by default.
    For advanced features, use get_advanced_retry_handler() or set use_advanced_features=True.

    Args:
        **kwargs: Configuration parameters for the retry handler

    Returns:
        UnifiedRetryHandler: Configured retry handler instance
    """
    # Default to basic features unless explicitly requested
    kwargs.setdefault("use_advanced_features", False)
    return UnifiedRetryHandler(**kwargs)


def get_advanced_retry_handler(**kwargs) -> UnifiedRetryHandler:
    """Get a retry handler with advanced features enabled.

    This function creates a retry handler with all advanced features enabled by default.

    Args:
        **kwargs: Configuration parameters for the retry handler

    Returns:
        UnifiedRetryHandler: Configured retry handler with advanced features
    """
    # Enable advanced features by default
    kwargs.setdefault("use_advanced_features", True)
    return UnifiedRetryHandler(**kwargs)
