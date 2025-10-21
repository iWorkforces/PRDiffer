"""Async parallel execution service for batch processing operations.

This module provides async parallel execution using asyncio.gather instead
of ThreadPoolExecutor for better performance and resource utilization.
"""

import asyncio
from typing import List, Callable, Any, Optional, Dict, Awaitable, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from ccpragents.infrastructure.logging.console_logger import get_logger


class ErrorHandlingStrategy(Enum):
    """Strategy for handling errors in parallel execution."""

    IGNORE = "ignore"  # Log and return None (backward compatible)
    RAISE = "raise"  # Raise the first exception encountered
    COLLECT = "collect"  # Collect all errors and return them
    CONTINUE = "continue"  # Continue processing, return results and errors


@dataclass
class BatchResult:
    """Result container for batch operations with error tracking."""

    successful: List[Any]
    failed: List[Tuple[Any, BaseException]]  # BaseException to handle all exception types
    total_processed: int

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_processed == 0:
            return 0.0
        return (len(self.successful) / self.total_processed) * 100


class AsyncParallelExecutor:
    """Service for executing async operations in parallel using asyncio.

    This class provides utilities for parallel execution of async operations
    with better performance than thread-based approaches.
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        timeout: Optional[float] = None,
        error_strategy: ErrorHandlingStrategy = ErrorHandlingStrategy.IGNORE,
        logger=None,
    ):
        """Initialize the async parallel executor.

        Args:
            max_concurrent: Maximum number of concurrent operations
            timeout: Timeout for individual operations (optional)
            error_strategy: Strategy for handling errors (default: IGNORE for backward compatibility)
            logger: Logger instance for logging operations
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.error_strategy = error_strategy
        self._logger = logger or get_logger()
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_batch(
        self, func: Callable[[Any], Awaitable[Any]], items: List[Any], *args, **kwargs
    ) -> Union[List[Any], BatchResult]:
        """Execute an async function on a list of items in parallel.

        Args:
            func: Async function to execute for each item
            items: List of items to process
            *args: Additional positional arguments for the function
            **kwargs: Additional keyword arguments for the function

        Returns:
            List of results (IGNORE strategy) or BatchResult (other strategies)
        """
        if not items:
            if self.error_strategy == ErrorHandlingStrategy.IGNORE:
                return []
            return BatchResult(successful=[], failed=[], total_processed=0)

        successful_results = []
        failed_items = []

        async def process_with_semaphore(
            item: Any,
        ) -> Tuple[Any, Optional[Any], Optional[Exception]]:
            """Process item with concurrency limit, returning (item, result, exception)."""
            async with self._semaphore:
                try:
                    if self.timeout:
                        result = await asyncio.wait_for(
                            func(item, *args, **kwargs), timeout=self.timeout
                        )
                    else:
                        result = await func(item, *args, **kwargs)
                    return (item, result, None)
                except asyncio.TimeoutError as e:
                    self._logger.error(
                        f"Timeout processing item {item} after {self.timeout}s"
                    )
                    return (item, None, e)
                except Exception as e:
                    self._logger.error(f"Error processing item {item}: {e}")
                    return (item, None, e)

        # Execute all tasks concurrently with return_exceptions=True to prevent cancellation
        results = await asyncio.gather(
            *[process_with_semaphore(item) for item in items],
            return_exceptions=True,
        )

        # Process results based on error strategy
        for result in results:
            if isinstance(result, BaseException):
                # This is an unexpected exception from gather itself
                # (could be Exception, KeyboardInterrupt, SystemExit, etc.)
                self._logger.error(f"Unexpected gather exception: {result}")
                if self.error_strategy == ErrorHandlingStrategy.RAISE:
                    raise result
                failed_items.append((None, result))
            else:
                # Result is a tuple from process_with_semaphore
                item, value, exception = result
                if exception is None:
                    successful_results.append(value)
                else:
                    if self.error_strategy == ErrorHandlingStrategy.RAISE:
                        raise exception
                    failed_items.append((item, exception))

        # Return based on strategy
        if self.error_strategy == ErrorHandlingStrategy.IGNORE:
            # Backward compatible: return only successful results
            return successful_results
        else:
            return BatchResult(
                successful=successful_results,
                failed=failed_items,
                total_processed=len(items),
            )

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
    ) -> Union[List[Any], BatchResult]:
        """Execute async function with progress tracking.

        Args:
            func: Async function to execute for each item
            items: List of items to process
            progress_callback: Optional callback(completed, total) for progress
            *args: Additional positional arguments for the function
            **kwargs: Additional keyword arguments for the function

        Returns:
            List of results (IGNORE strategy) or BatchResult (other strategies)
        """
        if not items:
            if self.error_strategy == ErrorHandlingStrategy.IGNORE:
                return []
            return BatchResult(successful=[], failed=[], total_processed=0)

        total = len(items)
        progress_lock = asyncio.Lock()  # Lock for thread-safe counter updates
        progress_counter = {"completed": 0}  # Use dict to avoid nonlocal issues
        successful_results = []
        failed_items = []

        async def process_with_progress(
            item: Any,
        ) -> Tuple[Any, Optional[Any], Optional[Exception]]:
            """Process item and update progress atomically."""
            async with self._semaphore:
                result = None
                exception: Optional[Exception] = None

                try:
                    if self.timeout:
                        result = await asyncio.wait_for(
                            func(item, *args, **kwargs), timeout=self.timeout
                        )
                    else:
                        result = await func(item, *args, **kwargs)
                except asyncio.TimeoutError as e:
                    self._logger.error(
                        f"Timeout processing item {item} after {self.timeout}s"
                    )
                    exception = e
                except Exception as e:
                    self._logger.error(f"Error processing item {item}: {e}")
                    exception = e

                # Atomic counter update and callback
                async with progress_lock:
                    progress_counter["completed"] += 1
                    current_count = progress_counter["completed"]

                    # Call progress callback while holding lock to ensure consistency
                    if progress_callback:
                        try:
                            progress_callback(current_count, total)
                        except Exception as callback_error:
                            self._logger.warning(
                                f"Progress callback error: {callback_error}"
                            )

                return (item, result, exception)

        # Execute all tasks concurrently with return_exceptions=True
        results = await asyncio.gather(
            *[process_with_progress(item) for item in items],
            return_exceptions=True,
        )

        # Process results based on error strategy
        for result in results:
            if isinstance(result, BaseException):
                # Unexpected exception from gather itself
                # (could be Exception, KeyboardInterrupt, SystemExit, etc.)
                self._logger.error(f"Unexpected gather exception: {result}")
                if self.error_strategy == ErrorHandlingStrategy.RAISE:
                    raise result
                failed_items.append((None, result))
            else:
                # Result is a tuple from process_with_semaphore
                item, value, exception = result
                if exception is None:
                    successful_results.append(value)
                else:
                    if self.error_strategy == ErrorHandlingStrategy.RAISE:
                        raise exception
                    failed_items.append((item, exception))

        # Return based on strategy
        if self.error_strategy == ErrorHandlingStrategy.IGNORE:
            return successful_results
        else:
            return BatchResult(
                successful=successful_results,
                failed=failed_items,
                total_processed=len(items),
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics.

        Returns:
            Dictionary containing executor statistics
        """
        return {
            "max_concurrent": self.max_concurrent,
            "timeout": self.timeout,
            "error_strategy": self.error_strategy.value,
            "semaphore_locked": self._semaphore.locked(),
            "available_permits": self._semaphore._value
            if hasattr(self._semaphore, "_value")
            else None,
        }


def get_async_parallel_executor(
    max_concurrent: int = 10,
    timeout: Optional[float] = None,
    error_strategy: ErrorHandlingStrategy = ErrorHandlingStrategy.IGNORE,
) -> AsyncParallelExecutor:
    """Get a configured async parallel executor instance.

    Args:
        max_concurrent: Maximum number of concurrent operations
        timeout: Timeout for individual operations (optional)
        error_strategy: Strategy for handling errors (default: IGNORE for backward compatibility)

    Returns:
        AsyncParallelExecutor: Configured async parallel executor instance
    """
    return AsyncParallelExecutor(
        max_concurrent=max_concurrent, timeout=timeout, error_strategy=error_strategy
    )
