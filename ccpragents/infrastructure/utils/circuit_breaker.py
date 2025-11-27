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
from typing import Optional
from enum import StrEnum

import anyio

from ccpragents.infrastructure.logging.console_logger import get_logger


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


def get_circuit_breaker(
    failure_threshold: int = 5, timeout: float = 60.0
) -> CircuitBreaker:
    """Get a configured circuit breaker instance.

    Args:
        failure_threshold: Number of failures before opening the circuit
        timeout: Time in seconds to keep circuit open before trying again

    Returns:
        CircuitBreaker: Configured circuit breaker instance
    """
    return CircuitBreaker(failure_threshold=failure_threshold, timeout=timeout)
