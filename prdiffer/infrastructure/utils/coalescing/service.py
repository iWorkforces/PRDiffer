"""Request coalescing service implementation.

This module provides the core implementation of request coalescing
to prevent duplicate API calls for the same resource.
"""

import anyio
import logging
from collections.abc import Callable, Awaitable
from typing import Any
from dataclasses import dataclass, field

from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.settings import get_settings_service
from prdiffer.domain.exceptions import PRDifferException
from prdiffer.domain.errors import E5001_INTERNAL_ERROR


DEFAULT_MAX_WAITERS = 100


@dataclass
class CoalescedRequest:
    """Data class representing a coalesced request."""

    key: str
    event: anyio.Event = field(default_factory=anyio.Event)
    result: Any | None = None
    exception: BaseException | None = None
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

    def __init__(self, logger: logging.Logger | None = None, max_waiters: int | None = None) -> None:
        """Initialize the request coalescing service.

        Args:
            logger: Logger instance for logging operations
            max_waiters: Maximum number of waiters per request (default: from settings or 100)
        """
        self._pending_requests: dict[str, CoalescedRequest] = {}
        self._lock = anyio.Lock()
        self._logger = logger or get_logger()

        if max_waiters is None:
            settings_service = get_settings_service()
            max_waiters = settings_service.get("request_coalescing.max_waiters", DEFAULT_MAX_WAITERS)
        if max_waiters is None:
            max_waiters = DEFAULT_MAX_WAITERS
        
        self._max_waiters = int(max_waiters)
        self._max_pending_requests = 1000  # Maximum concurrent unique requests (DoS prevention)

    async def coalesce(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
        timeout: float | None = 30.0,
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
        existing_request = None
        async with self._lock:
            if key in self._pending_requests:
                pending = self._pending_requests[key]

                if pending.request_count >= self._max_waiters:
                    self._logger.warning(f"Maximum waiters ({self._max_waiters}) reached for key '{key}', executing new request instead of waiting")
                else:
                    pending.request_count += 1
                    existing_request = pending
                    self._logger.debug(f"Coalescing request for key '{key}' (total waiting: {pending.request_count})")

        if existing_request is not None:
            effective_timeout = timeout if timeout is not None else 30.0
            return await self._wait_for_request(existing_request, key, effective_timeout)

        new_request: CoalescedRequest | None = None
        async with self._lock:
            if key in self._pending_requests:
                pending = self._pending_requests[key]

                if pending.request_count >= self._max_waiters:
                    self._logger.warning(f"Maximum waiters ({self._max_waiters}) reached for key '{key}', executing new request instead of waiting")
                else:
                    pending.request_count += 1
                    existing_request = pending

            if existing_request is None:
                # Check if we've reached max pending requests limit (DoS prevention)
                if len(self._pending_requests) >= self._max_pending_requests:
                    self._logger.warning(
                        f"Maximum pending requests ({self._max_pending_requests}) reached, "
                        f"evicting oldest request"
                    )
                    # Evict oldest pending request (first key in dict)
                    if self._pending_requests:
                        oldest_key = next(iter(self._pending_requests))
                        oldest_request = self._pending_requests[oldest_key]
                        oldest_request.event.set()  # Signal waiters to stop waiting
                        oldest_request.exception = TimeoutError("Evicted due to pending request limit")
                        del self._pending_requests[oldest_key]
                        self._logger.info(f"Evicted pending request for key '{oldest_key}' to make room for new request")
                
                new_request = CoalescedRequest(key=key)
                self._pending_requests[key] = new_request
                self._logger.debug(f"Starting new request for key '{key}' (total pending: {len(self._pending_requests)})")

        if existing_request is not None:
            effective_timeout = timeout if timeout is not None else 30.0
            return await self._wait_for_request(existing_request, key, effective_timeout)

        if new_request is None:
            raise PRDifferException(
                f"Internal error: Request for key '{key}' should be owned by this task "
                "but new_request is None. This indicates a logic error in request coalescing.",
                error_code=E5001_INTERNAL_ERROR,
            )

        effective_timeout = timeout if timeout is not None else 30.0
        return await self._execute_request(new_request, key, fetch_func, effective_timeout)

    async def _wait_for_request(self, existing_request: CoalescedRequest, key: str, timeout: float) -> Any:
        """Wait for an existing request to complete."""
        try:
            with anyio.fail_after(timeout):
                await existing_request.event.wait()

            if existing_request.exception is not None:
                raise existing_request.exception

            self._logger.debug("Request coalesced for key '{key}' - returning cached result")
            return existing_request.result
        except TimeoutError:
            self._logger.error(f"Coalesced request timed out for key '{key}'")
            raise
        except RuntimeError, AttributeError, KeyError:
            self._logger.error(f"Coalesced request failed for key '{key}'")
            raise
        finally:
            await self._decrement_waiter(key)

    async def _execute_request(
        self,
        new_request: CoalescedRequest,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
        timeout: float,
    ) -> Any:
        """Execute the fetch function and share the result with waiters."""
        cleanup_done = False
        try:
            with anyio.fail_after(timeout):
                result = await fetch_func()

            async with self._lock:
                if key in self._pending_requests and self._pending_requests[key] is new_request:
                    waiter_count = self._pending_requests[key].request_count
                    new_request.result = result
                    new_request.event.set()
                    del self._pending_requests[key]
                    cleanup_done = True
                    self._logger.info(f"Request completed for key '{key}' (served {waiter_count} waiters)")
                else:
                    new_request.result = result
                    new_request.event.set()
                    cleanup_done = True
                    self._logger.warning(f"Request completed for key '{key}' but state was modified")

            return result

        except TimeoutError:
            await self._cleanup_on_failure(key, new_request, cleanup_done)
            exc = TimeoutError(f"Request timed out after {timeout} seconds")
            new_request.exception = exc
            new_request.event.set()
            self._logger.error(f"Request timed out for key '{key}' after {timeout} seconds")
            raise exc

        except Exception as e:
            await self._cleanup_on_failure(key, new_request, cleanup_done)
            new_request.exception = e
            new_request.event.set()
            self._logger.error(f"Request failed for key '{key}': {e}")
            raise

    async def _decrement_waiter(self, key: str) -> None:
        """Safely decrement waiter count with cleanup."""
        async with self._lock:
            if key in self._pending_requests:
                pending = self._pending_requests[key]
                pending.request_count -= 1

                if pending.request_count <= 0 and pending.event.is_set():
                    del self._pending_requests[key]
                    self._logger.debug(f"Cleaned up request for key '{key}' (no more waiters)")

    async def _cleanup_on_failure(self, key: str, request: CoalescedRequest, cleanup_done: bool) -> None:
        """Clean up a request on failure or timeout."""
        if cleanup_done:
            return

        async with self._lock:
            if key in self._pending_requests and self._pending_requests[key] is request:
                del self._pending_requests[key]
                self._logger.debug(f"Cleaned up failed request for key '{key}'")

    async def clear(self) -> None:
        """Clear all pending requests."""
        async with self._lock:
            self._pending_requests.clear()
            self._logger.info("Cleared all pending requests")

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about pending requests."""
        async with self._lock:
            pending_count = len(self._pending_requests)
            pending_keys = list(self._pending_requests.keys())
            total_waiters = sum(req.request_count for req in self._pending_requests.values())

        return {
            "pending_count": pending_count,
            "pending_keys": pending_keys,
            "total_waiters": total_waiters,
        }


_request_coalescing_service: RequestCoalescingService | None = None


def get_request_coalescing_service() -> RequestCoalescingService:
    """Get the global request coalescing service instance.

    Returns:
        RequestCoalescingService: The global instance
    """
    global _request_coalescing_service
    if _request_coalescing_service is None:
        _request_coalescing_service = RequestCoalescingService()
    return _request_coalescing_service
