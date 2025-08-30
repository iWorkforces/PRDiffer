"""Advanced retry handler with circuit breaker, health tracking, and context-aware strategies."""
import time
import random
from typing import Any, Callable, Optional, Dict
from enum import StrEnum

from ccpragents.domain.services.retry import RetryServiceInterface
from ccpragents.infrastructure.logging.console_logger import get_logger
from ccpragents.infrastructure.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from ccpragents.infrastructure.utils.api_health_tracker import APIHealthTracker


class OperationContext(StrEnum):
    """Context types for different operations."""
    REPOSITORY_ACCESS = "repository_access"
    FILE_CONTENT = "file_content"
    PULL_REQUEST = "pull_request"
    BATCH_OPERATION = "batch_operation"


class AdvancedRetryHandler(RetryServiceInterface):
    """Advanced retry handler with circuit breaker, health tracking, and context-aware strategies.

    Provides enterprise-grade resilience with:
    - Circuit breaker pattern for cascading failure prevention
    - API health tracking for adaptive retry delays
    - Context-aware retry strategies
    - Comprehensive error categorization
    """

    def __init__(self,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 retry_on_404: bool = False,
                 retry_on_403: bool = True,
                 retry_on_500: bool = True,
                 retry_log_level: str = "DEBUG",
                 permanent_failure_log_level: str = "INFO",
                 # Phase 3 parameters
                 circuit_breaker_enabled: bool = True,
                 circuit_breaker_failure_threshold: int = 5,
                 circuit_breaker_timeout: float = 60.0,
                 adaptive_retry_enabled: bool = True,
                 max_adaptive_delay: float = 30.0,
                 api_health_tracking: bool = True,
                 context_aware_retry: bool = True,
                 logger=None):
        """Initialize the advanced retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            retry_on_404: Whether to retry 404 (Not Found) errors
            retry_on_403: Whether to retry 403 (Forbidden) errors
            retry_on_500: Whether to retry 5xx server errors
            retry_log_level: Log level for retry attempts
            permanent_failure_log_level: Log level for permanent failures
            circuit_breaker_enabled: Enable circuit breaker pattern
            circuit_breaker_failure_threshold: Failures before opening circuit
            circuit_breaker_timeout: Seconds to keep circuit open
            adaptive_retry_enabled: Enable adaptive retry delays
            max_adaptive_delay: Maximum adaptive delay in seconds
            api_health_tracking: Enable API health tracking
            context_aware_retry: Enable context-aware retry strategies
            logger: Logger instance for retry events
        """
        # Basic retry configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_on_404 = retry_on_404
        self.retry_on_403 = retry_on_403
        self.retry_on_500 = retry_on_500
        self.retry_log_level = retry_log_level.upper()
        self.permanent_failure_log_level = permanent_failure_log_level.upper()

        # Phase 3 configuration
        self.circuit_breaker_enabled = circuit_breaker_enabled
        self.adaptive_retry_enabled = adaptive_retry_enabled
        self.max_adaptive_delay = max_adaptive_delay
        self.api_health_tracking = api_health_tracking
        self.context_aware_retry = context_aware_retry

        self._logger = logger or get_logger()

        # Initialize Phase 3 components
        self._circuit_breaker: Optional[CircuitBreaker] = None
        if circuit_breaker_enabled:
            self._circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_failure_threshold,
                timeout=circuit_breaker_timeout,
                logger=self._logger
            )

        self._health_tracker: Optional[APIHealthTracker] = None
        if api_health_tracking:
            self._health_tracker = APIHealthTracker(logger=self._logger)

        # Context-specific retry configurations
        self._context_configs: Dict[OperationContext, Dict] = {
            OperationContext.REPOSITORY_ACCESS: {
                "max_retries": max_retries,
                "retry_delay": retry_delay * 2,  # Longer delays for repo access
                "backoff_multiplier": 2.0
            },
            OperationContext.FILE_CONTENT: {
                "max_retries": max_retries - 1,  # Fewer retries for file content
                "retry_delay": retry_delay,
                "backoff_multiplier": 1.5
            },
            OperationContext.PULL_REQUEST: {
                "max_retries": max_retries + 1,  # More retries for PR data
                "retry_delay": retry_delay,
                "backoff_multiplier": 2.0
            },
            OperationContext.BATCH_OPERATION: {
                "max_retries": max_retries - 1,  # Fewer retries for batch ops
                "retry_delay": retry_delay * 0.5,  # Shorter delays
                "backoff_multiplier": 1.5
            }
        }

    def execute_with_retry(self,
                          func: Callable,
                          *args,
                          context: Optional[OperationContext] = None,
                          **kwargs) -> Any:
        """Execute a function with advanced retry logic.

        Args:
            func: Function to execute with retry logic
            *args: Positional arguments for the function
            context: Operation context for context-aware retry
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the successful function call

        Raises:
            Exception: If all retry attempts fail or circuit breaker is open
        """
        # Check circuit breaker
        if self._circuit_breaker and self.circuit_breaker_enabled:
            if not self._circuit_breaker.can_execute():
                raise CircuitBreakerOpenException(
                    f"Circuit breaker is open. State: {self._circuit_breaker.state.value}"
                )

        # Get context-specific configuration
        config = self._get_context_config(context)
        max_retries = config["max_retries"]
        base_delay = config["retry_delay"]
        backoff_multiplier = config["backoff_multiplier"]

        last_exception = None
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)

                # Record success
                self._record_success(start_time)
                return result

            except Exception as e:
                last_exception = e

                # Record failure
                self._record_failure(e)

                # Check if this error should be retried
                should_retry = self._should_retry_error(e, context)
                is_last_attempt = attempt == max_retries - 1

                if not should_retry or is_last_attempt:
                    self._log_permanent_failure(e, should_retry, is_last_attempt)
                    raise

                # Calculate adaptive delay
                delay = self._calculate_adaptive_delay(attempt, e, base_delay, backoff_multiplier)

                # Log retry attempt
                self._log_retry_attempt(attempt, delay, e, context)

                time.sleep(delay)

        # Fallback (should not reach here)
        if last_exception:
            raise last_exception

    def _get_context_config(self, context: Optional[OperationContext]) -> Dict:
        """Get configuration for specific operation context.

        Args:
            context: Operation context

        Returns:
            dict: Context-specific configuration
        """
        if context and self.context_aware_retry and context in self._context_configs:
            return self._context_configs[context]

        # Default configuration
        return {
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "backoff_multiplier": 2.0
        }

    def _should_retry_error(self, error: Exception, context: Optional[OperationContext] = None) -> bool:
        """Determine if an error should be retried with context awareness.

        Args:
            error: Exception to check
            context: Operation context

        Returns:
            bool: True if this error should be retried
        """
        error_str = str(error).lower()

        # Basic error classification (from Phase 2)
        if "404" in error_str and not self.retry_on_404:
            return False
        if "403" in error_str and not self.retry_on_403:
            return False
        if any(f"{code}" in error_str for code in [500, 501, 502, 503, 504]) and not self.retry_on_500:
            return False

        # Context-aware retry logic
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
            self._is_rate_limit_error(error) or
            "timeout" in error_str or
            "connection" in error_str or
            "network" in error_str or
            "503" in error_str or
            "502" in error_str or
            "504" in error_str
        )

    def _calculate_adaptive_delay(self, attempt: int, error: Exception, 
                                base_delay: float, backoff_multiplier: float) -> float:
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
        exponential_delay = base_delay * (backoff_multiplier ** attempt)

        # Add jitter
        jitter = random.uniform(0, exponential_delay * 0.1)
        delay_with_jitter = exponential_delay + jitter

        # Adaptive delay based on API health
        if self.adaptive_retry_enabled and self._health_tracker:
            adaptive_delay = self._health_tracker.get_recommended_delay(
                delay_with_jitter, self.max_adaptive_delay
            )
            return adaptive_delay

        # Rate limit errors get longer delays
        if self._is_rate_limit_error(error):
            return min(delay_with_jitter * 2, self.max_adaptive_delay)

        return delay_with_jitter

    def _record_success(self, start_time: float):
        """Record a successful operation.

        Args:
            start_time: Start time of the operation
        """
        duration = time.time() - start_time

        if self._circuit_breaker:
            self._circuit_breaker.record_success()

        if self._health_tracker:
            self._health_tracker.record_call(duration, success=True)

    def _record_failure(self, error: Exception):
        """Record a failed operation.

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

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an exception indicates a rate limit error."""
        error_str = str(error).lower()
        return "rate limit" in error_str or "429" in str(error)

    def _log_retry_attempt(self, attempt: int, delay: float, error: Exception, 
                          context: Optional[OperationContext] = None):
        """Log retry attempt with context information."""
        is_rate_limit = self._is_rate_limit_error(error)
        context_str = f" [{context.value}]" if context else ""

        if is_rate_limit:
            message = (
                f"Rate limit hit{context_str}, retrying in {delay:.2f}s "
                f"(attempt {attempt + 1})"
            )
        else:
            error_msg = str(error)
            if len(error_msg) > 100:
                error_msg = error_msg[:97] + "..."
            message = (
                f"API error{context_str}, retrying in {delay:.2f}s "
                f"(attempt {attempt + 1}): {error_msg}"
            )

        self._log_at_level(message, self.retry_log_level)

    def _log_permanent_failure(self, error: Exception, should_retry: bool, is_last_attempt: bool):
        """Log permanent failure information."""
        if not should_retry:
            error_msg = str(error)
            if len(error_msg) > 150:
                error_msg = error_msg[:147] + "..."
            message = f"Permanent failure (no retry configured): {error_msg}"
            self._log_at_level(message, self.permanent_failure_log_level)
        elif is_last_attempt:
            message = f"All retry attempts exhausted: {str(error)[:100]}..."
            self._log_at_level(message, "ERROR")

    def _log_at_level(self, message: str, level: str):
        """Log message at specified level."""
        level = level.upper()
        log_method = getattr(self._logger, level.lower(), self._logger.info)
        log_method(message)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive retry handler statistics."""
        stats: Dict[str, Any] = {
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            "adaptive_retry_enabled": self.adaptive_retry_enabled,
            "api_health_tracking": self.api_health_tracking,
            "context_aware_retry": self.context_aware_retry
        }

        if self._circuit_breaker:
            stats["circuit_breaker"] = self._circuit_breaker.get_stats()

        if self._health_tracker:
            stats["api_health"] = self._health_tracker.get_stats()

        return stats


def get_advanced_retry_handler(**kwargs) -> AdvancedRetryHandler:
    """Get a configured advanced retry handler instance.

    Args:
        **kwargs: Configuration parameters for the retry handler

    Returns:
        AdvancedRetryHandler: Configured advanced retry handler instance
    """
    return AdvancedRetryHandler(**kwargs)
