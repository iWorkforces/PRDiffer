"""Request coalescing service for deduplicating concurrent requests.

This module provides request coalescing to prevent duplicate API calls
for the same resource when multiple concurrent requests arrive.
"""

import anyio
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from ccpragents.infrastructure.logging.console_logger import get_logger


@dataclass
class CoalescedRequest:
    """Data class representing a coalesced request."""

    key: str
    event: anyio.Event = field(default_factory=anyio.Event)
    result: Optional[Any] = None
    exception: Optional[BaseException] = None
    created_at: datetime = field(default_factory=datetime.now)
    request_count: int = 1


class RequestCoalescingService:
    """Service for coalescing duplicate concurrent requests.

    This service ensures that when multiple concurrent requests are made for
    the same resource, only one actual API call is made and all requesters
    receive the same result.
    """

    def __init__(self, logger=None):
        """Initialize the request coalescing service.

        Args:
            logger: Logger instance for logging operations
        """
        self._pending_requests: Dict[str, CoalescedRequest] = {}
        self._lock = anyio.Lock()
        self._logger = logger or get_logger()

    async def coalesce(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
        timeout: Optional[float] = 30.0,
    ) -> Any:
        """Coalesce requests for the same key with timeout protection.

        If a request for this key is already in progress, wait for its result.
        Otherwise, execute the fetch function and share the result with all waiters.

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
                    f"Request coalesced for key '{key}' - returning cached result"
                )
                return existing_request.result
            except TimeoutError:
                self._logger.error(f"Coalesced request timed out for key '{key}'")
                raise
            except Exception as e:
                self._logger.error(f"Coalesced request failed for key '{key}': {e}")
                raise
            finally:
                # Decrement waiter count for coalesced requests
                async with self._lock:
                    if key in self._pending_requests:
                        self._pending_requests[key].request_count -= 1

        # Phase 3: Create new request (double-check pattern with proper locking)
        new_request: Optional[CoalescedRequest] = None
        async with self._lock:
            # Double-check after acquiring lock
            if key in self._pending_requests:
                # Another task created the request while we were waiting for lock
                pending = self._pending_requests[key]
                pending.request_count += 1
                existing_request = pending
            else:
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
            finally:
                # Decrement waiter count
                async with self._lock:
                    if key in self._pending_requests:
                        self._pending_requests[key].request_count -= 1

        # Phase 5: Execute the fetch function (we own the request)
        assert new_request is not None, "new_request should be set when owning request"

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
            # Handle timeout
            async with self._lock:
                if (
                    not cleanup_done
                    and key in self._pending_requests
                    and self._pending_requests[key] is new_request
                ):
                    exc = TimeoutError(f"Request timed out after {timeout} seconds")
                    new_request.exception = exc
                    new_request.event.set()
                    del self._pending_requests[key]
                    cleanup_done = True
            self._logger.error(
                f"Request timed out for key '{key}' after {timeout} seconds"
            )
            raise

        except Exception as e:
            # Handle other exceptions
            async with self._lock:
                if (
                    not cleanup_done
                    and key in self._pending_requests
                    and self._pending_requests[key] is new_request
                ):
                    new_request.exception = e
                    new_request.event.set()
                    del self._pending_requests[key]
                    cleanup_done = True
            self._logger.error(f"Request failed for key '{key}': {e}")
            raise

    async def clear(self) -> None:
        """Clear all pending requests.

        This will not cancel in-flight requests, but will remove them from tracking.
        """
        async with self._lock:
            self._pending_requests.clear()
            self._logger.info("Cleared all pending requests")

    async def get_stats(self) -> Dict[str, Any]:
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
