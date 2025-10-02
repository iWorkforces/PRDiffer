"""Async parallel execution service for batch processing operations.

This module provides async parallel execution using asyncio.gather instead
of ThreadPoolExecutor for better performance and resource utilization.
"""

import asyncio
from typing import List, Callable, Any, Optional, Dict, Awaitable
from ccpragents.infrastructure.logging.console_logger import get_logger


class AsyncParallelExecutor:
    """Service for executing async operations in parallel using asyncio.

    This class provides utilities for parallel execution of async operations
    with better performance than thread-based approaches.
    """

    def __init__(
        self, max_concurrent: int = 10, timeout: Optional[float] = None, logger=None
    ):
        """Initialize the async parallel executor.

        Args:
            max_concurrent: Maximum number of concurrent operations
            timeout: Timeout for individual operations (optional)
            logger: Logger instance for logging operations
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self._logger = logger or get_logger()
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_batch(
        self, func: Callable[[Any], Awaitable[Any]], items: List[Any], *args, **kwargs
    ) -> List[Any]:
        """Execute an async function on a list of items in parallel.

        Args:
            func: Async function to execute for each item
            items: List of items to process
            *args: Additional positional arguments for the function
            **kwargs: Additional keyword arguments for the function

        Returns:
            List of results from the function calls (excludes None results)
        """
        if not items:
            return []

        async def process_with_semaphore(item: Any) -> Optional[Any]:
            """Process item with concurrency limit."""
            async with self._semaphore:
                try:
                    if self.timeout:
                        result = await asyncio.wait_for(
                            func(item, *args, **kwargs), timeout=self.timeout
                        )
                    else:
                        result = await func(item, *args, **kwargs)
                    return result
                except asyncio.TimeoutError:
                    self._logger.error(
                        f"Timeout processing item {item} after {self.timeout}s"
                    )
                    return None
                except Exception as e:
                    self._logger.error(f"Error processing item {item}: {e}")
                    return None

        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[process_with_semaphore(item) for item in items],
            return_exceptions=False,
        )

        # Filter out None results
        return [r for r in results if r is not None]

    async def execute_batch_with_context(
        self,
        func: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        items: List[Any],
        context: Dict[str, Any],
    ) -> List[Any]:
        """Execute an async function on items with shared context in parallel.

        Args:
            func: Async function to execute (should accept item and context)
            items: List of items to process
            context: Shared context dictionary passed to each function call

        Returns:
            List of results from the function calls (excludes None results)
        """
        if not items:
            return []

        async def process_with_semaphore(item: Any) -> Optional[Any]:
            """Process item with concurrency limit and context."""
            async with self._semaphore:
                try:
                    if self.timeout:
                        result = await asyncio.wait_for(
                            func(item, context), timeout=self.timeout
                        )
                    else:
                        result = await func(item, context)
                    return result
                except asyncio.TimeoutError:
                    self._logger.error(
                        f"Timeout processing item {item} after {self.timeout}s"
                    )
                    return None
                except Exception as e:
                    self._logger.error(f"Error processing item {item}: {e}")
                    return None

        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[process_with_semaphore(item) for item in items],
            return_exceptions=False,
        )

        # Filter out None results
        return [r for r in results if r is not None]

    async def execute_mapped_batch(
        self,
        func_map: Dict[Any, Callable[[Any], Awaitable[Any]]],
        items: List[Any],
        default_func: Optional[Callable[[Any], Awaitable[Any]]] = None,
        **kwargs,
    ) -> List[Any]:
        """Execute different async functions based on item type/key in parallel.

        Args:
            func_map: Dictionary mapping item keys/types to async functions
            items: List of items to process
            default_func: Default async function if item not found in func_map
            **kwargs: Additional keyword arguments for all functions

        Returns:
            List of results from the function calls (excludes None results)
        """
        if not items:
            return []

        async def process_with_semaphore(item: Any) -> Optional[Any]:
            """Process item with appropriate function and concurrency limit."""
            async with self._semaphore:
                # Determine which function to use
                func = None
                if hasattr(item, "__class__"):
                    func = func_map.get(type(item))
                if func is None:
                    func = func_map.get(item)
                if func is None and default_func:
                    func = default_func

                if func is None:
                    self._logger.warning(f"No function found for item: {item}")
                    return None

                try:
                    if self.timeout:
                        result = await asyncio.wait_for(
                            func(item, **kwargs), timeout=self.timeout
                        )
                    else:
                        result = await func(item, **kwargs)
                    return result
                except asyncio.TimeoutError:
                    self._logger.error(
                        f"Timeout processing item {item} after {self.timeout}s"
                    )
                    return None
                except Exception as e:
                    self._logger.error(f"Error processing item {item}: {e}")
                    return None

        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[process_with_semaphore(item) for item in items],
            return_exceptions=False,
        )

        # Filter out None results
        return [r for r in results if r is not None]

    async def execute_with_progress(
        self,
        func: Callable[[Any], Awaitable[Any]],
        items: List[Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        *args,
        **kwargs,
    ) -> List[Any]:
        """Execute async function with progress tracking.

        Args:
            func: Async function to execute for each item
            items: List of items to process
            progress_callback: Optional callback(completed, total) for progress
            *args: Additional positional arguments for the function
            **kwargs: Additional keyword arguments for the function

        Returns:
            List of results from the function calls (excludes None results)
        """
        if not items:
            return []

        total = len(items)
        completed = 0
        results = []
        progress_lock = asyncio.Lock()  # Lock for thread-safe counter updates

        async def process_with_progress(item: Any) -> Optional[Any]:
            """Process item and update progress."""
            nonlocal completed
            async with self._semaphore:
                try:
                    if self.timeout:
                        result = await asyncio.wait_for(
                            func(item, *args, **kwargs), timeout=self.timeout
                        )
                    else:
                        result = await func(item, *args, **kwargs)

                    # Thread-safe counter update
                    async with progress_lock:
                        completed += 1
                        current_count = completed

                    if progress_callback:
                        progress_callback(current_count, total)

                    return result
                except Exception as e:
                    self._logger.error(f"Error processing item {item}: {e}")

                    # Thread-safe counter update
                    async with progress_lock:
                        completed += 1
                        current_count = completed

                    if progress_callback:
                        progress_callback(current_count, total)
                    return None

        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[process_with_progress(item) for item in items],
            return_exceptions=False,
        )

        # Filter out None results
        return [r for r in results if r is not None]

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics.

        Returns:
            Dictionary containing executor statistics
        """
        return {
            "max_concurrent": self.max_concurrent,
            "timeout": self.timeout,
            "semaphore_locked": self._semaphore.locked(),
        }


def get_async_parallel_executor(
    max_concurrent: int = 10, timeout: Optional[float] = None
) -> AsyncParallelExecutor:
    """Get a configured async parallel executor instance.

    Args:
        max_concurrent: Maximum number of concurrent operations
        timeout: Timeout for individual operations (optional)

    Returns:
        AsyncParallelExecutor: Configured async parallel executor instance
    """
    return AsyncParallelExecutor(max_concurrent=max_concurrent, timeout=timeout)
