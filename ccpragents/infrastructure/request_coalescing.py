"""Request coalescing service for deduplicating concurrent requests.

This module provides request coalescing to prevent duplicate API calls
for the same resource when multiple concurrent requests arrive.
"""

import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
from ccpragents.infrastructure.logging.console_logger import get_logger


@dataclass
class CoalescedRequest:
    """Data class representing a coalesced request."""

    key: str
    future: asyncio.Future
    created_at: datetime
    request_count: int


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
        self._lock = asyncio.Lock()
        self._logger = logger or get_logger()

    async def coalesce(self, key: str, fetch_func: Callable[[], Awaitable[Any]]) -> Any:
        """Coalesce requests for the same key.

        If a request for this key is already in progress, wait for its result.
        Otherwise, execute the fetch function and share the result with all waiters.

        Args:
            key: Unique key identifying the request (e.g., "owner/repo/pr/123")
            fetch_func: Async function to fetch the data if not already pending

        Returns:
            The result from the fetch function

        Raises:
            Exception: Any exception raised by the fetch function
        """
        async with self._lock:
            # Check if request is already pending
            if key in self._pending_requests:
                pending = self._pending_requests[key]
                pending.request_count += 1
                self._logger.debug(
                    f"Coalescing request for key '{key}' "
                    f"(total waiting: {pending.request_count})"
                )
                # Release lock before waiting
                future = pending.future

        # If we found a pending request, wait for it outside the lock
        if key in self._pending_requests:
            try:
                result = await future
                self._logger.debug(
                    f"Request coalesced for key '{key}' - returning cached result"
                )
                return result
            except Exception as e:
                self._logger.error(f"Coalesced request failed for key '{key}': {e}")
                raise

        # No pending request, create a new one
        async with self._lock:
            # Double-check (race condition prevention)
            if key in self._pending_requests:
                future = self._pending_requests[key].future
            else:
                # Create new future for this request
                future = asyncio.Future()
                self._pending_requests[key] = CoalescedRequest(
                    key=key,
                    future=future,
                    created_at=datetime.now(),
                    request_count=1,
                )
                self._logger.debug(f"Starting new request for key '{key}'")

        # If we found an existing request after double-check, wait for it
        if key in self._pending_requests and self._pending_requests[key].future is not future:
            return await future

        # Execute the fetch function outside the lock
        try:
            result = await fetch_func()
            future.set_result(result)
            waiter_count = self._pending_requests.get(key, CoalescedRequest(key, future, datetime.now(), 1)).request_count
            self._logger.info(
                f"Request completed for key '{key}' (served {waiter_count} waiters)"
            )
            return result
        except Exception as e:
            future.set_exception(e)
            self._logger.error(f"Request failed for key '{key}': {e}")
            raise
        finally:
            # Clean up pending request (safe to do outside lock since we're done)
            async with self._lock:
                if key in self._pending_requests:
                    del self._pending_requests[key]

    async def clear(self) -> None:
        """Clear all pending requests.

        This will not cancel in-flight requests, but will remove them from tracking.
        """
        async with self._lock:
            self._pending_requests.clear()
            self._logger.info("Cleared all pending requests")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about pending requests.

        Returns:
            Dictionary containing statistics
        """
        return {
            "pending_count": len(self._pending_requests),
            "pending_keys": list(self._pending_requests.keys()),
            "total_waiters": sum(
                req.request_count for req in self._pending_requests.values()
            ),
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
