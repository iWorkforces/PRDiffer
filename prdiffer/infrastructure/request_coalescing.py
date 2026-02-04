"""Request coalescing service for deduplicating concurrent requests.

This module provides request coalescing to prevent duplicate API calls
for the same resource when multiple concurrent requests arrive.
"""

import anyio
from typing import Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.settings import get_settings_service
from prdiffer.domain.exceptions import PRDifferException
from prdiffer.domain.errors import E5001_INTERNAL_ERROR


# Default maximum number of waiters per request to prevent resource exhaustion
DEFAULT_MAX_WAITERS = 100


@dataclass
class CoalescedRequest:
    """Data class representing a coalesced request."""

    key: str
    event: anyio.Event = field(default_factory=anyio.Event)
    result: Optional[Any] = None
    exception: Optional[BaseException] = None
    request_count: int = 1


class RequestCoalescingService:
    """Service for coalescing duplicate concurrent requests.

    This service ensures that when multiple concurrent requests are made for
    the same resource, only one actual API call is made and all requesters
    receive the same result.

    Memory Safety:
    - Maximum waiter limit prevents unbounded waiter accumulation
    - Proper cleanup on success, failure, timeout, and cancellation
    - Atomic state management with anyio.Lock
    """

    def __init__(self, logger=None, max_waiters: Optional[int] = None):
        """Initialize the request coalescing service.

        Args:
            logger: Logger instance for logging operations
            max_waiters: Maximum number of waiters per request (default: from settings or 100)
        """
        self._pending_requests: dict[str, CoalescedRequest] = {}
        self._lock = anyio.Lock()
        self._logger = logger or get_logger()

        # Load max_waiters from settings if not provided
        if max_waiters is None:
            settings_service = get_settings_service()
            max_waiters = settings_service.get(
                "request_coalescing.max_waiters", DEFAULT_MAX_WAITERS
            )

        self._max_waiters = max_waiters

    async def coalesce(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
        timeout: Optional[float] = 30.0,
    ) -> Any:
        """Coalesce requests for the same key with timeout protection.

        If a request for this key is already in progress, wait for its result.
        Otherwise, execute the fetch function and share the result with all waiters.

        Memory Safety:
        - Maximum waiter limit enforced before waiting
        - Proper cleanup on all exit paths (success, failure, timeout)
        - Atomic state transitions prevent race conditions

        Args:
            key: Unique key identifying the request (e.g., "owner/repo/pr/123")
            fetch_func: Async function to fetch the data if not already pending
            timeout: Maximum time to wait for the fetch function (default: 30 seconds)

        Returns:
            The result from the fetch function

        Raises:
            TimeoutError: If the fetch function times out
            Exception: Any exception raised by the fetch function
        """
        # Phase 1: Check for existing request and increment waiter count atomically
        existing_request = None
        async with self._lock:
            if key in self._pending_requests:
                pending = self._pending_requests[key]

                # Enforce maximum waiter limit to prevent resource exhaustion
                if pending.request_count >= self._max_waiters:
                    self._logger.warning(
                        f"Maximum waiters ({self._max_waiters}) reached for key '{key}', "
                        "executing new request instead of waiting"
                    )
                    # Don't wait, fall through to create a new request
                else:
                    pending.request_count += 1
                    existing_request = pending
                    self._logger.debug(
                        f"Coalescing request for key '{key}' "
                        f"(total waiting: {pending.request_count})"
                    )

        # Phase 2: Wait for existing request with timeout (outside lock)
        if existing_request is not None:
            try:
                # Wait for the event to be set
                with anyio.fail_after(timeout):
                    await existing_request.event.wait()

                # Check if there was an exception
                if existing_request.exception is not None:
                    raise existing_request.exception

                self._logger.debug(
                    "Request coalesced for key '{key}' - returning cached result"
                )
                return existing_request.result
            except TimeoutError:
                self._logger.error(f"Coalesced request timed out for key '{key}'")
                raise
            except RuntimeError, AttributeError, KeyError:
                self._logger.error(f"Coalesced request failed for key '{key}'")
                raise
            finally:
                # Clean up even on failure
                await self._decrement_waiter(key)

        # Phase 3: Create new request (double-check pattern with proper locking)
        new_request: Optional[CoalescedRequest] = None
        async with self._lock:
            # Double-check after acquiring lock
            if key in self._pending_requests:
                # Another task created the request while we were waiting for lock
                pending = self._pending_requests[key]

                # Enforce maximum waiter limit
                if pending.request_count >= self._max_waiters:
                    self._logger.warning(
                        f"Maximum waiters ({self._max_waiters}) reached for key '{key}', "
                        "executing new request instead of waiting"
                    )
                else:
                    pending.request_count += 1
                    existing_request = pending

            if existing_request is None:
                # We're the first - create the request
                new_request = CoalescedRequest(key=key)
                self._pending_requests[key] = new_request
                self._logger.debug(f"Starting new request for key '{key}'")

        # Phase 4: If another task created the request, wait for it
        if existing_request is not None:
            try:
                with anyio.fail_after(timeout):
                    await existing_request.event.wait()

                if existing_request.exception is not None:
                    raise existing_request.exception
                return existing_request.result
            except TimeoutError:
                self._logger.error(f"Coalesced request timed out for key '{key}'")
                raise
            except RuntimeError, AttributeError, KeyError:
                self._logger.error(f"Coalesced request failed for key '{key}'")
                raise
            finally:
                await self._decrement_waiter(key)

        # Phase 5: Execute the fetch function (we own the request)
        # Check that we own the request (replace assertion with proper exception)
        if new_request is None:
            raise PRDifferException(
                f"Internal error: Request for key '{key}' should be owned by this task "
                "but new_request is None. This indicates a logic error in request coalescing.",
                error_code=E5001_INTERNAL_ERROR,
            )

        cleanup_done = False
        try:
            # Execute with timeout protection
            with anyio.fail_after(timeout):
                result = await fetch_func()

            # Set result while holding lock to ensure atomicity
            async with self._lock:
                if (
                    key in self._pending_requests
                    and self._pending_requests[key] is new_request
                ):
                    waiter_count = self._pending_requests[key].request_count
                    # Set result before removing from dict to avoid race
                    new_request.result = result
                    new_request.event.set()
                    del self._pending_requests[key]
                    cleanup_done = True
                    self._logger.info(
                        f"Request completed for key '{key}' (served {waiter_count} waiters)"
                    )
                else:
                    # Edge case: request was somehow replaced or removed
                    new_request.result = result
                    new_request.event.set()
                    cleanup_done = True
                    self._logger.warning(
                        f"Request completed for key '{key}' but state was modified"
                    )

            return result

        except TimeoutError:
            # Handle timeout with proper cleanup
            await self._cleanup_on_failure(key, new_request, cleanup_done)
            exc = TimeoutError(f"Request timed out after {timeout} seconds")
            new_request.exception = exc
            new_request.event.set()
            self._logger.error(
                f"Request timed out for key '{key}' after {timeout} seconds"
            )
            raise exc

        except Exception as e:
            # Handle other exceptions with proper cleanup
            await self._cleanup_on_failure(key, new_request, cleanup_done)
            new_request.exception = e
            new_request.event.set()
            self._logger.error(f"Request failed for key '{key}': {e}")
            raise

    async def _decrement_waiter(self, key: str) -> None:
        """Safely decrement waiter count with cleanup.

        If waiter count reaches zero and the request is completed,
        remove it from pending requests.

        Args:
            key: The request key to decrement waiter count for
        """
        async with self._lock:
            if key in self._pending_requests:
                pending = self._pending_requests[key]
                pending.request_count -= 1

                # Clean up if no more waiters and event is set (request completed)
                if pending.request_count <= 0 and pending.event.is_set():
                    del self._pending_requests[key]
                    self._logger.debug(
                        f"Cleaned up request for key '{key}' (no more waiters)"
                    )

    async def _cleanup_on_failure(
        self, key: str, request: CoalescedRequest, cleanup_done: bool
    ) -> None:
        """Clean up a request on failure or timeout.

        Args:
            key: The request key
            request: The coalesced request to clean up
            cleanup_done: Whether cleanup was already done
        """
        if cleanup_done:
            return

        async with self._lock:
            if key in self._pending_requests and self._pending_requests[key] is request:
                del self._pending_requests[key]
                self._logger.debug(f"Cleaned up failed request for key '{key}'")

    async def clear(self) -> None:
        """Clear all pending requests.

        This will not cancel in-flight requests, but will remove them from tracking.
        """
        async with self._lock:
            self._pending_requests.clear()
            self._logger.info("Cleared all pending requests")

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about pending requests.

        Returns:
            Dictionary containing statistics
        """
        async with self._lock:
            # Create a snapshot of the data under lock
            pending_count = len(self._pending_requests)
            pending_keys = list(self._pending_requests.keys())
            total_waiters = sum(
                req.request_count for req in self._pending_requests.values()
            )

        return {
            "pending_count": pending_count,
            "pending_keys": pending_keys,
            "total_waiters": total_waiters,
        }


# Global instance for singleton pattern
_request_coalescing_service: Optional[RequestCoalescingService] = None


def get_request_coalescing_service() -> RequestCoalescingService:
    """Get the global request coalescing service instance.

    Returns:
        RequestCoalescingService: The global instance
    """
    global _request_coalescing_service
    if _request_coalescing_service is None:
        _request_coalescing_service = RequestCoalescingService()
    return _request_coalescing_service
