"""Circuit breaker pattern implementation for GitHub API resilience.

This module provides a thread-safe circuit breaker implementation that prevents
cascading failures by temporarily stopping calls to a failing service.

Thread Safety:
- All state mutations are protected by threading.Lock() for synchronous contexts
- For async contexts, use the async-compatible methods (async_record_success, async_record_failure)
  which use anyio.Lock() for non-blocking synchronization
"""

import time
import threading
from typing import Dict, List, Optional
from enum import StrEnum

import anyio

from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.domain.exceptions import PRDifferException
from prdiffer.domain.errors import E5001_INTERNAL_ERROR


class CircuitState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit open, fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Thread-safe circuit breaker implementation for API resilience.

    Prevents cascading failures by temporarily stopping calls to a failing service
    and allowing it time to recover.

    Thread Safety:
    - Uses threading.Lock() for synchronous operations
    - Provides async methods using anyio.Lock() for non-blocking async operations
    """

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0, logger=None):
        """Initialize the circuit breaker.

        Args:
            failure_threshold: Number of failures before opening the circuit
            timeout: Time in seconds to keep circuit open before trying again
            logger: Logger instance for circuit breaker events
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self._logger = logger or get_logger()

        # Thread safety locks
        self._sync_lock = threading.Lock()
        self._async_lock: Optional[anyio.Lock] = None  # Lazy initialization

        # Circuit state (protected by locks)
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._successful_calls = 0

    def _get_async_lock(self) -> anyio.Lock:
        """Get or create the async lock (lazy initialization).

        Returns:
            anyio.Lock: The async lock for async context operations
        """
        if self._async_lock is None:
            self._async_lock = anyio.Lock()
        return self._async_lock

    @property
    def state(self) -> CircuitState:
        """Get current circuit state (thread-safe read)."""
        with self._sync_lock:
            return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count (thread-safe read)."""
        with self._sync_lock:
            return self._failure_count

    def can_execute(self) -> bool:
        """Check if execution is allowed based on circuit state (thread-safe).

        Returns:
            bool: True if execution is allowed, False otherwise
        """
        with self._sync_lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if timeout has elapsed
                if (
                    self._last_failure_time
                    and time.time() - self._last_failure_time >= self.timeout
                ):
                    self._transition_to_half_open_unlocked()
                    return True
                return False

            # HALF_OPEN state
            return True

    async def can_execute_async(self) -> bool:
        """Async version of can_execute (non-blocking).

        Returns:
            bool: True if execution is allowed, False otherwise
        """
        async with self._get_async_lock():
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if timeout has elapsed
                if (
                    self._last_failure_time
                    and time.time() - self._last_failure_time >= self.timeout
                ):
                    self._transition_to_half_open_unlocked()
                    return True
                return False

            # HALF_OPEN state
            return True

    def record_success(self):
        """Record a successful operation (thread-safe)."""
        with self._sync_lock:
            self._record_success_unlocked()

    async def record_success_async(self):
        """Async version of record_success (non-blocking)."""
        async with self._get_async_lock():
            self._record_success_unlocked()

    def _record_success_unlocked(self):
        """Record a successful operation (must be called with lock held)."""
        if self._state == CircuitState.HALF_OPEN:
            self._successful_calls += 1
            # Reset circuit after successful call in half-open state
            self._transition_to_closed_unlocked()
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            if self._failure_count > 0:
                self._failure_count = 0
                self._logger.debug("Circuit breaker: Reset failure count after success")

    def record_failure(self):
        """Record a failed operation (thread-safe)."""
        with self._sync_lock:
            self._record_failure_unlocked()

    async def record_failure_async(self):
        """Async version of record_failure (non-blocking)."""
        async with self._get_async_lock():
            self._record_failure_unlocked()

    def _record_failure_unlocked(self):
        """Record a failed operation (must be called with lock held)."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to_open_unlocked()
        elif self._state == CircuitState.HALF_OPEN:
            # Failure in half-open state, go back to open
            self._transition_to_open_unlocked()

    def _transition_to_open(self):
        """Transition circuit to OPEN state (thread-safe)."""
        with self._sync_lock:
            self._transition_to_open_unlocked()

    def _transition_to_open_unlocked(self):
        """Transition circuit to OPEN state (must be called with lock held)."""
        self._state = CircuitState.OPEN
        self._logger.warning(
            f"Circuit breaker OPENED: {self._failure_count} failures reached threshold {self.failure_threshold}"
        )

    def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state (thread-safe)."""
        with self._sync_lock:
            self._transition_to_half_open_unlocked()

    def _transition_to_half_open_unlocked(self):
        """Transition circuit to HALF_OPEN state (must be called with lock held)."""
        self._state = CircuitState.HALF_OPEN
        self._successful_calls = 0
        self._logger.info(
            "Circuit breaker transitioned to HALF_OPEN: Testing service recovery"
        )

    def _transition_to_closed(self):
        """Transition circuit to CLOSED state (thread-safe)."""
        with self._sync_lock:
            self._transition_to_closed_unlocked()

    def _transition_to_closed_unlocked(self):
        """Transition circuit to CLOSED state (must be called with lock held)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._successful_calls = 0
        self._logger.info("Circuit breaker CLOSED: Service recovered")

    def get_stats(self) -> dict:
        """Get circuit breaker statistics (thread-safe).

        Returns:
            dict: Circuit breaker statistics
        """
        with self._sync_lock:
            return {
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "timeout": self.timeout,
                "last_failure_time": self._last_failure_time,
                "successful_calls": self._successful_calls,
            }


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, message: str = "Circuit breaker is open"):
        self.message = message
        super().__init__(self.message)


class GlobalCircuitBreakerRegistry:
    """Global registry for circuit breakers shared across all API clients.

    This singleton class manages circuit breakers for different endpoints,
    allowing shared state across the application for better failure coordination.

    Features:
    - Per-endpoint circuit breakers for targeted failure handling
    - Global circuit breaker for system-wide protection
    - Configurable default thresholds
    - Statistics aggregation across all breakers
    """

    _instance: Optional["GlobalCircuitBreakerRegistry"] = None
    _lock = threading.Lock()
    _initialized: bool = False

    def __new__(
        cls,
        default_failure_threshold: int = 5,
        default_timeout: float = 60.0,
    ) -> "GlobalCircuitBreakerRegistry":
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        # Type narrowing: instance is guaranteed to be initialized here
        if cls._instance is None:
            raise PRDifferException(
                "Singleton instance not initialized", error_code=E5001_INTERNAL_ERROR
            )
        return cls._instance

    def __init__(
        self,
        default_failure_threshold: int = 5,
        default_timeout: float = 60.0,
    ):
        """Initialize the global circuit breaker registry.

        Args:
            default_failure_threshold: Default failures before opening circuit
            default_timeout: Default timeout for open circuits
        """
        if self._initialized:
            return

        self._default_failure_threshold = default_failure_threshold
        self._default_timeout = default_timeout
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._registry_lock = threading.Lock()
        self._logger = get_logger()

        # Global circuit breaker for system-wide protection
        self._global_breaker = CircuitBreaker(
            failure_threshold=default_failure_threshold
            * 2,  # Higher threshold for global
            timeout=default_timeout,
            logger=self._logger,
        )

        self._initialized = True

    def get_breaker(self, endpoint: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a specific endpoint.

        Args:
            endpoint: Identifier for the endpoint (e.g., "github_api", "repo_content")

        Returns:
            CircuitBreaker: Circuit breaker for the endpoint
        """
        with self._registry_lock:
            if endpoint not in self._breakers:
                self._breakers[endpoint] = CircuitBreaker(
                    failure_threshold=self._default_failure_threshold,
                    timeout=self._default_timeout,
                    logger=self._logger,
                )
                self._logger.debug(f"Created circuit breaker for endpoint: {endpoint}")
            return self._breakers[endpoint]

    @property
    def global_breaker(self) -> CircuitBreaker:
        """Get the global circuit breaker."""
        return self._global_breaker

    def can_execute(self, endpoint: Optional[str] = None) -> bool:
        """Check if execution is allowed for an endpoint.

        Checks both the endpoint-specific breaker and the global breaker.

        Args:
            endpoint: Specific endpoint to check (optional)

        Returns:
            bool: True if execution is allowed
        """
        # Check global breaker first
        if not self._global_breaker.can_execute():
            return False

        # Check endpoint-specific breaker if provided
        if endpoint:
            breaker = self.get_breaker(endpoint)
            if not breaker.can_execute():
                return False

        return True

    async def can_execute_async(self, endpoint: Optional[str] = None) -> bool:
        """Async version of can_execute.

        Args:
            endpoint: Specific endpoint to check (optional)

        Returns:
            bool: True if execution is allowed
        """
        # Check global breaker first
        if not await self._global_breaker.can_execute_async():
            return False

        # Check endpoint-specific breaker if provided
        if endpoint:
            breaker = self.get_breaker(endpoint)
            if not await breaker.can_execute_async():
                return False

        return True

    def record_success(self, endpoint: Optional[str] = None) -> None:
        """Record a successful operation.

        Args:
            endpoint: Specific endpoint that succeeded (optional)
        """
        self._global_breaker.record_success()
        if endpoint:
            self.get_breaker(endpoint).record_success()

    async def record_success_async(self, endpoint: Optional[str] = None) -> None:
        """Async version of record_success.

        Args:
            endpoint: Specific endpoint that succeeded (optional)
        """
        await self._global_breaker.record_success_async()
        if endpoint:
            await self.get_breaker(endpoint).record_success_async()

    def record_failure(self, endpoint: Optional[str] = None) -> None:
        """Record a failed operation.

        Args:
            endpoint: Specific endpoint that failed (optional)
        """
        self._global_breaker.record_failure()
        if endpoint:
            self.get_breaker(endpoint).record_failure()

    async def record_failure_async(self, endpoint: Optional[str] = None) -> None:
        """Async version of record_failure.

        Args:
            endpoint: Specific endpoint that failed (optional)
        """
        await self._global_breaker.record_failure_async()
        if endpoint:
            await self.get_breaker(endpoint).record_failure_async()

    def get_all_stats(self) -> Dict[str, dict]:
        """Get statistics for all circuit breakers.

        Returns:
            Dict mapping endpoint names to their statistics
        """
        with self._registry_lock:
            stats = {"global": self._global_breaker.get_stats()}
            for endpoint, breaker in self._breakers.items():
                stats[endpoint] = breaker.get_stats()
            return stats

    def get_open_breakers(self) -> List[str]:
        """Get list of endpoints with open circuit breakers.

        Returns:
            List of endpoint names with open circuits
        """
        with self._registry_lock:
            open_breakers = []
            if self._global_breaker.state == CircuitState.OPEN:
                open_breakers.append("global")
            for endpoint, breaker in self._breakers.items():
                if breaker.state == CircuitState.OPEN:
                    open_breakers.append(endpoint)
            return open_breakers

    def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        with self._registry_lock:
            self._global_breaker._transition_to_closed()
            for breaker in self._breakers.values():
                breaker._transition_to_closed()
            self._logger.info("All circuit breakers reset to CLOSED")

    def clear_endpoint(self, endpoint: str) -> None:
        """Remove a specific endpoint's circuit breaker.

        Args:
            endpoint: Endpoint to remove
        """
        with self._registry_lock:
            if endpoint in self._breakers:
                del self._breakers[endpoint]
                self._logger.debug(f"Removed circuit breaker for endpoint: {endpoint}")


# Global registry instance (singleton)
_global_circuit_breaker_registry: Optional[GlobalCircuitBreakerRegistry] = None


def get_global_circuit_breaker_registry(
    default_failure_threshold: int = 5,
    default_timeout: float = 60.0,
) -> GlobalCircuitBreakerRegistry:
    """Get the global circuit breaker registry singleton.

    Args:
        default_failure_threshold: Default failures before opening circuit
        default_timeout: Default timeout for open circuits

    Returns:
        GlobalCircuitBreakerRegistry: The global registry instance
    """
    global _global_circuit_breaker_registry
    if _global_circuit_breaker_registry is None:
        _global_circuit_breaker_registry = GlobalCircuitBreakerRegistry(
            default_failure_threshold=default_failure_threshold,
            default_timeout=default_timeout,
        )
    return _global_circuit_breaker_registry
