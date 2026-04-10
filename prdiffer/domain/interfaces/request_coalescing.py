"""Protocol definition for request coalescing/deduplication.

This module defines the RequestCoalescingProtocol that infrastructure
implementations must satisfy, following Clean Architecture principles.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RequestCoalescingProtocol(Protocol):
    """Protocol for request deduplication.

    Defines the contract for coalescing duplicate concurrent requests
    so only one API call is made and all requesters receive the same result.
    """

    async def coalesce(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
        timeout: float | None = 30.0,
    ) -> Any:
        """Coalesce requests for the same key with timeout protection.

        If a request for this key is already in progress, wait for its result.
        Otherwise, execute the fetch function and share the result with all waiters.

        Args:
            key: Unique key identifying the request to coalesce
            fetch_func: Async callable that performs the actual fetch
            timeout: Maximum time to wait for the result

        Returns:
            The result from the fetch function
        """
        ...

    async def clear(self) -> None:
        """Clear all pending requests."""
        ...

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about pending coalesced requests.

        Returns:
            Dictionary with pending_count, pending_keys, and total_waiters
        """
        ...
