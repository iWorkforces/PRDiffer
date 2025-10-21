"""Async parallel execution service for batch processing operations.

This module provides async parallel execution using anyio task groups instead
of ThreadPoolExecutor for better performance and resource utilization.
"""

import anyio
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
    failed: List[
        Tuple[Any, BaseException]
    ]  # BaseException to handle all exception types
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
        self._semaphore = anyio.Semaphore(max_concurrent)

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
        results: List[Tuple[Any, Optional[Any], Optional[Exception]]] = []

        async def process_with_semaphore(
            item: Any, index: int
        ) -> None:
            """Process item with concurrency limit, storing result at index."""
            async with self._semaphore:
                try:
                    if self.timeout:
                        with anyio.fail_after(self.timeout):
                            result = await func(item, *args, **kwargs)
                    else:
                        result = await func(item, *args, **kwargs)
                    results[index] = (item, result, None)
                except TimeoutError as e:
                    self._logger.error(
                        f"Timeout processing item {item} after {self.timeout}s"
                    )
                    results[index] = (item, None, e)
                except Exception as e:
                    self._logger.error(f"Error processing item {item}: {e}")
                    results[index] = (item, None, e)

        # Initialize results list with placeholders
        results = [(None, None, None) for _ in items]

        # Execute all tasks concurrently using task group
        try:
            async with anyio.create_task_group() as tg:
                for index, item in enumerate(items):
                    tg.start_soon(process_with_semaphore, item, index)
        except BaseException as e:
            # Task group raises first exception if error_strategy is RAISE
            # For other strategies, exceptions are captured in results
            if self.error_strategy == ErrorHandlingStrategy.RAISE:
                raise
            self._logger.error(f"Unexpected task group exception: {e}")
            failed_items.append((None, e))

        # Process results based on error strategy
        for result in results:
            if result == (None, None, None):
                # Placeholder not replaced - task was cancelled or didn't run
                continue
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

        results: List[Optional[Any]] = [None for _ in items]

        async def process_with_semaphore(item: Any, index: int) -> None:
            """Process item with concurrency limit and context."""
            async with self._semaphore:
                try:
                    if self.timeout:
                        with anyio.fail_after(self.timeout):
                            result = await func(item, context)
                    else:
                        result = await func(item, context)
                    results[index] = result
                except TimeoutError:
                    self._logger.error(
                        f"Timeout processing item {item} after {self.timeout}s"
                    )
                except Exception as e:
                    self._logger.error(f"Error processing item {item}: {e}")

        # Execute all tasks concurrently
        async with anyio.create_task_group() as tg:
            for index, item in enumerate(items):
                tg.start_soon(process_with_semaphore, item, index)

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

        results: List[Optional[Any]] = [None for _ in items]

        async def process_with_semaphore(item: Any, index: int) -> None:
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
                    return

                try:
                    if self.timeout:
                        with anyio.fail_after(self.timeout):
                            result = await func(item, **kwargs)
                    else:
                        result = await func(item, **kwargs)
                    results[index] = result
                except TimeoutError:
                    self._logger.error(
                        f"Timeout processing item {item} after {self.timeout}s"
                    )
                except Exception as e:
                    self._logger.error(f"Error processing item {item}: {e}")

        # Execute all tasks concurrently
        async with anyio.create_task_group() as tg:
            for index, item in enumerate(items):
                tg.start_soon(process_with_semaphore, item, index)

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
        progress_lock = anyio.Lock()  # Lock for thread-safe counter updates
        progress_counter = {"completed": 0}  # Use dict to avoid nonlocal issues
        successful_results = []
        failed_items = []
        results: List[Tuple[Any, Optional[Any], Optional[Exception]]] = []

        async def process_with_progress(
            item: Any, index: int
        ) -> None:
            """Process item and update progress atomically."""
            async with self._semaphore:
                result = None
                exception: Optional[Exception] = None

                try:
                    if self.timeout:
                        with anyio.fail_after(self.timeout):
                            result = await func(item, *args, **kwargs)
                    else:
                        result = await func(item, *args, **kwargs)
                except TimeoutError as e:
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

                results[index] = (item, result, exception)

        # Initialize results list with placeholders
        results = [(None, None, None) for _ in items]

        # Execute all tasks concurrently with task group
        try:
            async with anyio.create_task_group() as tg:
                for index, item in enumerate(items):
                    tg.start_soon(process_with_progress, item, index)
        except BaseException as e:
            # Task group raises first exception if error_strategy is RAISE
            if self.error_strategy == ErrorHandlingStrategy.RAISE:
                raise
            self._logger.error(f"Unexpected task group exception: {e}")
            failed_items.append((None, e))

        # Process results based on error strategy
        for result in results:
            if result == (None, None, None):
                # Placeholder not replaced - task was cancelled or didn't run
                continue
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
        # Note: anyio.Semaphore doesn't have locked() method like asyncio
        # We can check the statistics attribute if available
        semaphore_stats = None
        if hasattr(self._semaphore, "statistics"):
            semaphore_stats = self._semaphore.statistics()

        return {
            "max_concurrent": self.max_concurrent,
            "timeout": self.timeout,
            "error_strategy": self.error_strategy.value,
            "semaphore_stats": semaphore_stats,
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
