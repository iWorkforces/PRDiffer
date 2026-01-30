"""Unified retry handler utility for GitHub API operations with optional advanced features.

This module provides a unified retry handler that combines basic retry logic with
optional advanced features like circuit breaker, health tracking, and context-aware strategies.

The handler supports both synchronous and asynchronous operations:
- UnifiedRetryHandler: Synchronous version using time.sleep()
- execute_with_retry_async(): Async version using anyio.sleep() (non-blocking)

Common logic is extracted to BaseUnifiedRetryHandler to avoid code duplication.
"""

import random
import time
import threading
from abc import abstractmethod
from typing import Any, Callable, Optional, Dict, Coroutine, TypeVar, Tuple

import anyio

from enum import StrEnum
from typing import Type, cast

from prdiffer.domain.services import RetryServiceInterface
from prdiffer.infrastructure.utils.logger_factory import get_logger
from prdiffer.infrastructure.utils.retry_logger import (
    log_retry_attempt,
    log_permanent_failure,
)
from prdiffer.infrastructure.utils.error_classifier import (
    categorize_error,
    is_secondary_rate_limit_error,
    is_rate_limit_error as is_rate_limit_error_classifier,
    classify_error_for_retry,
)
from prdiffer.infrastructure.utils.rate_limit_parser import (
    RateLimitInfo,
    extract_rate_limit_info,
    is_rate_limit_remaining_below_threshold,
)
from prdiffer.infrastructure.utils.delay_calculator import (
    calculate_retry_delay as calculate_retry_delay_impl,
)


T = TypeVar("T")


try:  # pragma: no cover - optional dependency for type narrowing
    from github import GithubException as PyGithubException
except Exception:  # pragma: no cover - fallback when PyGithub isn't available
    PyGithubException: Optional[Type[BaseException]] = None


# Exceptions to catch in retry operations
# Note: We deliberately exclude KeyboardInterrupt, SystemExit, and GeneratorExit
# to allow system-level exceptions to propagate for proper shutdown/cleanup.
RETRY_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
    # Network and timeout exceptions (transient)
    TimeoutError,
    ConnectionError,
    OSError,
    # Common runtime exceptions
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    AttributeError,
    LookupError,
    EOFError,
    IOError,
    ImportError,
    ArithmeticError,
    FloatingPointError,
    OverflowError,
    ZeroDivisionError,
    AssertionError,
    NameError,
    UnboundLocalError,
    UnicodeError,
    UnicodeDecodeError,
    UnicodeEncodeError,
    UnicodeTranslateError,
)

if PyGithubException is not None:
    RETRY_EXCEPTIONS = RETRY_EXCEPTIONS + (PyGithubException,)


class OperationContext(StrEnum):
    """Context types for different operations."""

    REPOSITORY_ACCESS = "repository_access"
    FILE_CONTENT = "file_content"
    PULL_REQUEST = "pull_request"
    BATCH_OPERATION = "batch_operation"


class BaseUnifiedRetryHandler(RetryServiceInterface):
    """Base class for unified retry handlers with common logic.

    This base class contains all shared retry logic, configuration,
    error classification, and helper methods. Subclasses implement
    the execution and sleep methods for sync/async variations.

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
        rate_limit_remaining_threshold: int = 1,
        rate_limit_reset_buffer: float = 1.0,
        secondary_rate_limit_backoff: float = 60.0,
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
            rate_limit_remaining_threshold: Remaining requests threshold for rate-limit handling
            rate_limit_reset_buffer: Seconds to add to reset-based delay
            secondary_rate_limit_backoff: Base delay in seconds for secondary rate limits
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
        self.rate_limit_remaining_threshold = rate_limit_remaining_threshold
        self.rate_limit_reset_buffer = rate_limit_reset_buffer
        self.secondary_rate_limit_backoff = secondary_rate_limit_backoff

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

    @abstractmethod
    def _execute_and_sleep(
        self,
        func: Callable,
        args: Tuple,
        kwargs: Dict,
        delay: float,
    ) -> Any:
        """Execute function and sleep before next retry.

        Subclasses implement this to handle sync/async execution and sleep.

        Args:
            func: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            delay: Delay in seconds before next retry

        Returns:
            Result of the function call
        """
        pass

    def _execute_with_retry_base(
        self,
        func: Callable,
        args: Tuple,
        kwargs: Dict,
        context: Optional[OperationContext] = None,
    ) -> Any:
        """Base retry logic shared by sync and async handlers.

        This method contains the common retry loop, error handling,
        and delay calculation. Subclasses call this after implementing
        _execute_and_sleep.

        Args:
            func: Function to execute with retry logic
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            context: Optional operation context for context-aware retry

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
                result = self._execute_and_sleep(func, args, kwargs, 0.0)

                # Record success if health tracking is enabled
                if self._health_tracker and start_time:
                    self._record_success(start_time)

                return result

            except RETRY_EXCEPTIONS as e:
                # Narrow type from BaseException to Exception since we excluded
                # KeyboardInterrupt, SystemExit, and GeneratorExit from RETRY_EXCEPTIONS
                exc = cast(Exception, e)
                last_exception = exc

                # Record failure for circuit breaker (always) and health tracker (if enabled)
                self._record_failure(exc)

                # Check if this error should be retried
                should_retry = self._should_retry_error(exc, context)
                is_last_attempt = attempt == max_retries - 1

                if not should_retry or is_last_attempt:
                    # Log permanent failure or final attempt
                    log_permanent_failure(
                        self._get_logger(),
                        exc,
                        self.permanent_failure_log_level,
                        should_retry,
                        is_last_attempt,
                    )
                    raise

                # Calculate delay (adaptive if enabled, basic otherwise)
                rate_limit_info = extract_rate_limit_info(exc)
                is_secondary_rate_limit = is_secondary_rate_limit_error(exc)
                delay = self._calculate_retry_delay(
                    attempt,
                    exc,
                    base_delay,
                    backoff_multiplier,
                    use_adaptive=self.adaptive_retry_enabled,
                    rate_limit_info=rate_limit_info,
                    is_secondary_rate_limit=is_secondary_rate_limit,
                )

                # Log the retry attempt
                log_retry_attempt(
                    self._get_logger(),
                    attempt,
                    delay,
                    exc,
                    self.retry_log_level,
                    context.value if context else None,
                    rate_limit_info=rate_limit_info,
                    is_secondary_rate_limit=is_secondary_rate_limit,
                    is_rate_limit_checker=self._is_rate_limit_error,
                )

                # Sleep before next retry (actual execution handled by _execute_and_sleep)
                self._execute_and_sleep(lambda: None, (), {}, delay)

        # This should not be reached, but just in case
        if last_exception:
            raise last_exception

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

        # Use error classifier for basic decision
        decision = classify_error_for_retry(
            error,
            retry_on_404=self.retry_on_404,
            retry_on_403=self.retry_on_403,
            retry_on_500=self.retry_on_500,
        )

        if not decision.should_retry:
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

        return True

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an exception indicates a rate limit error.

        Args:
            error: Exception to check

        Returns:
            bool: True if this is a rate limit error, False otherwise
        """
        return is_rate_limit_error_classifier(error)

    def _calculate_retry_delay(
        self,
        attempt: int,
        error: Exception,
        base_delay: float,
        backoff_multiplier: float,
        use_adaptive: bool,
        rate_limit_info: Optional[RateLimitInfo],
        is_secondary_rate_limit: bool,
    ) -> float:
        """Calculate retry delay based on error type and configuration.

        Args:
            attempt: Current attempt number (0-based)
            error: Exception that caused the retry
            base_delay: Base delay for this context
            backoff_multiplier: Backoff multiplier for this context
            use_adaptive: Whether to use adaptive retry delays
            rate_limit_info: Parsed rate limit information
            is_secondary_rate_limit: Whether this is a secondary rate limit error

        Returns:
            float: Delay in seconds
        """
        return calculate_retry_delay_impl(
            attempt=attempt,
            error=error,
            base_delay=base_delay,
            backoff_multiplier=backoff_multiplier,
            rate_limit_info=rate_limit_info,
            is_secondary_rate_limit=is_secondary_rate_limit,
            use_adaptive=use_adaptive,
            secondary_backoff=self.secondary_rate_limit_backoff,
            reset_buffer=self.rate_limit_reset_buffer,
            health_tracker=self._health_tracker,
            max_adaptive_delay=self.max_adaptive_delay,
        )

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
            error_type = categorize_error(error)
            self._health_tracker.record_call(0.0, success=False, error_type=error_type)

    def _get_logger(self):
        """Get logger instance, lazily loading if needed to avoid circular imports.

        Uses double-checked locking pattern for thread safety.
        """
        if not self._logger_fetched:
            with self._logger_lock:
                # Double-check pattern to avoid race conditions
                if not self._logger_fetched:
                    self._logger = get_logger(__name__)
                    self._logger_fetched = True
        return self._logger

    def _log_retry_attempt(
        self,
        attempt: int,
        delay: float,
        error: Exception,
        context: Optional[OperationContext] = None,
        rate_limit_info: Optional[RateLimitInfo] = None,
        is_secondary_rate_limit: bool = False,
    ):
        """Log retry attempt information at configured level.

        Args:
            attempt: Current attempt number (0-based)
            delay: Delay before next retry in seconds
            error: Exception that caused the retry
            context: Optional operation context
            rate_limit_info: Parsed rate limit information
            is_secondary_rate_limit: Whether this is a secondary rate limit error
        """
        is_rate_limit = self._is_rate_limit_error(error)
        context_str = (
            f" [{context.value}]" if context and self.context_aware_retry else ""
        )

        if is_rate_limit:
            label = "Secondary rate limit" if is_secondary_rate_limit else "Rate limit"
            message = "%s hit%s, retrying in %.2fs (attempt %d)" % (
                label,
                context_str,
                delay,
                attempt + 1,
            )
        else:
            # Truncate long error messages for cleaner logs
            error_msg = str(error)
            if len(error_msg) > 100:
                error_msg = error_msg[:97] + "..."
            message = "API error%s, retrying in %.2fs (attempt %d): %s" % (
                context_str,
                delay,
                attempt + 1,
                error_msg,
            )

        # Log at configured level
        self._log_at_level(message, self.retry_log_level)

        if rate_limit_info:
            self._log_rate_limit_headers(rate_limit_info, is_secondary_rate_limit)

    def _log_rate_limit_headers(
        self, rate_limit_info: RateLimitInfo, is_secondary_rate_limit: bool
    ):
        """Log rate limit header information.

        Args:
            rate_limit_info: Parsed rate limit information
            is_secondary_rate_limit: Whether this is a secondary rate limit error
        """
        level = "WARNING" if is_secondary_rate_limit else "INFO"
        message = (
            "Rate limit headers: remaining=%s limit=%s reset=%s retry_after=%s"
            % (
                rate_limit_info.remaining,
                rate_limit_info.limit,
                rate_limit_info.reset_at,
                rate_limit_info.retry_after,
            )
        )
        self._log_at_level(message, level)

        if is_rate_limit_remaining_below_threshold(
            rate_limit_info, self.rate_limit_remaining_threshold
        ):
            threshold_message = "Rate limit remaining below threshold: %d <= %d" % (
                rate_limit_info.remaining,
                self.rate_limit_remaining_threshold,
            )
            self._log_at_level(threshold_message, "WARNING")

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


class UnifiedRetryHandler(BaseUnifiedRetryHandler):
    """Unified retry handler supporting both sync and async operations.

    For backward compatibility, this class provides both:
    - execute_with_retry(): Synchronous execution using time.sleep()
    - execute_with_retry_async(): Asynchronous execution using anyio.sleep()
    """

    def _execute_and_sleep(
        self,
        func: Callable,
        args: Tuple,
        kwargs: Dict,
        delay: float,
    ) -> Any:
        """Execute function and sleep (blocking).

        Args:
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            delay: Delay in seconds (ignored if 0.0)

        Returns:
            Result of the function call
        """
        result = func(*args, **kwargs)

        # Sleep only if delay > 0 (first attempt has delay=0)
        if delay > 0:
            time.sleep(delay)

        return result

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
        # Use the base class retry logic
        return self._execute_with_retry_base(func, args, kwargs, context)

    async def execute_with_retry_async(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args,
        context: Optional[OperationContext] = None,
        **kwargs,
    ) -> T:
        """Execute an async function with retry logic and exponential backoff (non-blocking).

        This method uses anyio.sleep() instead of time.sleep() to avoid
        blocking the event loop during retry delays.

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
        if self._circuit_breaker and self.circuit_breaker_enabled:
            if not self._circuit_breaker.can_execute():
                from prdiffer.infrastructure.utils.circuit_breaker import (
                    CircuitBreakerOpenException,
                )

                raise CircuitBreakerOpenException(
                    f"Circuit breaker is open. State: {self._circuit_breaker.state.value}"
                )

        config = self._get_context_config(context)
        max_retries = config["max_retries"]
        base_delay = config["retry_delay"]
        backoff_multiplier = config.get("backoff_multiplier", 2.0)

        last_exception: Optional[Exception] = None
        start_time = time.time() if self._health_tracker else None

        for attempt in range(max_retries):
            try:
                result = await func(*args, **kwargs)

                if self._health_tracker and start_time:
                    self._record_success(start_time)

                return result

            except RETRY_EXCEPTIONS as e:
                from typing import cast

                exc = cast(Exception, e)
                last_exception = exc

                self._record_failure(exc)

                should_retry = self._should_retry_error(exc, context)
                is_last_attempt = attempt == max_retries - 1

                if not should_retry or is_last_attempt:
                    self._log_permanent_failure(exc, should_retry, is_last_attempt)
                    raise

                rate_limit_info = extract_rate_limit_info(exc)
                is_secondary_rate_limit = is_secondary_rate_limit_error(exc)
                delay = self._calculate_retry_delay(
                    attempt,
                    exc,
                    base_delay,
                    backoff_multiplier,
                    use_adaptive=self.adaptive_retry_enabled,
                    rate_limit_info=rate_limit_info,
                    is_secondary_rate_limit=is_secondary_rate_limit,
                )

                log_retry_attempt(
                    self._get_logger(),
                    attempt,
                    delay,
                    exc,
                    self.retry_log_level,
                    context.value if context else None,
                    rate_limit_info=rate_limit_info,
                    is_secondary_rate_limit=is_secondary_rate_limit,
                    is_rate_limit_checker=self._is_rate_limit_error,
                )

                await anyio.sleep(delay)

        if last_exception:
            raise last_exception

        raise RuntimeError("Unexpected state: no result and no exception")


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
