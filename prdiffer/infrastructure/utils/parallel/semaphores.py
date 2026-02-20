"""Concurrency primitives and semaphore utilities for parallel execution."""

import anyio
from typing import Any


async def create_semaphore(max_concurrent: int) -> anyio.Semaphore:
    """Create a semaphore for concurrency control.

    Args:
        max_concurrent: Maximum number of concurrent operations

    Returns:
        Configured anyio Semaphore
    """
    return anyio.Semaphore(max_concurrent)


async def create_lock() -> anyio.Lock:
    """Create a lock for exclusive access.

    Returns:
        Configured anyio Lock
    """
    return anyio.Lock()


class SemaphoreManager:
    """Manages semaphore lifecycle for parallel execution."""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._semaphore: anyio.Semaphore | None = None

    async def get_semaphore(self) -> anyio.Semaphore:
        """Get or create the semaphore for concurrency control."""
        if self._semaphore is None:
            self._semaphore = anyio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def __aenter__(self) -> anyio.Semaphore:
        """Enter async context manager."""
        return await self.get_semaphore()

    async def __aexit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Exit async context manager."""
        pass


class LockManager:
    """Manages lock lifecycle for exclusive access."""

    def __init__(self):
        self._lock: anyio.Lock | None = None

    async def get_lock(self) -> anyio.Lock:
        """Get or create the lock for exclusive access."""
        if self._lock is None:
            self._lock = anyio.Lock()
        return self._lock

    async def __aenter__(self) -> anyio.Lock:
        """Enter async context manager."""
        return await self.get_lock()

    async def __aexit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Exit async context manager."""
        pass
