"""Async parallel executor using anyio task groups.

This module provides a native async parallel executor that replaces
ThreadPoolExecutor with anyio's structured concurrency primitives.
"""

from typing import Callable, Any, TypeVar, Awaitable, cast

import anyio
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.utils.parallel.results import BatchResult, ErrorStrategy

# Exceptions to catch in parallel execution
# Note: We deliberately exclude KeyboardInterrupt, SystemExit, and GeneratorExit
# to allow system-level exceptions to propagate for proper shutdown/cleanup.
OPERATIONAL_EXCEPTIONS: tuple[type[BaseException], ...] = (
    TimeoutError,  # Timeout scenarios
    ConnectionError,  # Network issues
    OSError,  # File I/O errors
    RuntimeError,  # General runtime errors
    ValueError,  # Invalid values
    TypeError,  # Type errors
    KeyError,  # Missing key errors
    IndexError,  # Index out of range
    AttributeError,  # Attribute errors
    LookupError,  # Base for KeyError, IndexError
    EOFError,  # End of file
    IOError,  # I/O errors
    ImportError,  # Import errors
    ArithmeticError,  # Arithmetic errors
    FloatingPointError,  # Floating point errors
    OverflowError,  # Overflow errors
    ZeroDivisionError,  # Division by zero
    AssertionError,  # Assertion failures
    NameError,  # Name not found
    UnboundLocalError,  # Unbound local variable
    UnicodeError,  # Unicode errors
    UnicodeDecodeError,  # Unicode decode errors
    UnicodeEncodeError,  # Unicode encode errors
    UnicodeTranslateError,  # Unicode translate errors
)

T = TypeVar("T")
R = TypeVar("R")


class AsyncParallelExecutor:
    """Native async parallel executor using anyio task groups.

    This class provides parallel execution using anyio's structured concurrency
    primitives instead of ThreadPoolExecutor, offering better performance for
    I/O-bound async operations.

    Features:
    - Uses anyio.create_task_group() for structured concurrency
    - Semaphore-based concurrency control
    - Multiple error handling strategies
    - Progress tracking support
    - Timeout protection via anyio.fail_after()
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        timeout: float | None = None,
        error_strategy: ErrorStrategy = ErrorStrategy.IGNORE,
        logger: Any | None = None,
    ):
        """Initialize the async parallel executor.

        Args:
            max_concurrent: Maximum concurrent operations (semaphore limit)
            timeout: Timeout for entire batch operation (optional)
            error_strategy: How to handle errors during execution
            logger: Logger instance for logging operations
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.error_strategy = error_strategy
        self._logger = logger or get_logger()
        self._semaphore: anyio.Semaphore | None = None

    async def _get_semaphore(self) -> anyio.Semaphore:
        """Get or create the semaphore for concurrency control."""
        if self._semaphore is None:
            self._semaphore = anyio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def execute_batch(
        self,
        func: Callable[[T], Awaitable[R]],
        items: list[T],
    ) -> list[R]:
        """Execute an async function on a list of items in parallel.

        Args:
            func: Async function to execute for each item
            items: list of items to process

        Returns:
            list of results from function calls (errors filtered based on strategy)

        Raises:
            Exception: If error_strategy is RAISE and any operation fails
        """
        if not items:
            return []

        results: list[R] = []
        errors: list[tuple[T, Exception]] = []
        semaphore = await self._get_semaphore()

        async def process_item(item: T) -> None:
            async with semaphore:
                try:
                    result = await func(item)
                    if result is not None:
                        results.append(result)
                except OPERATIONAL_EXCEPTIONS as e:
                    if self.error_strategy == ErrorStrategy.RAISE:
                        raise
                    errors.append((item, cast(Exception, e)))
                    self._logger.error(f"Error processing item {item}: {e}")

        try:
            if self.timeout:
                with anyio.fail_after(self.timeout):
                    async with anyio.create_task_group() as tg:
                        for item in items:
                            tg.start_soon(process_item, item)
            else:
                async with anyio.create_task_group() as tg:
                    for item in items:
                        tg.start_soon(process_item, item)
        except TimeoutError:
            self._logger.warning(f"Batch execution timed out after {self.timeout}s")
            if self.error_strategy == ErrorStrategy.RAISE:
                raise

        if errors:
            self._logger.warning(f"Failed to process {len(errors)} items out of {len(items)}")

        return results

    async def execute_batch_with_context(
        self,
        func: Callable[[T, dict[str, Any]], Awaitable[R]],
        items: list[T],
        context: dict[str, Any],
    ) -> list[R]:
        """Execute an async function on items with shared context in parallel.

        Args:
            func: Async function to execute (accepts item and context)
            items: list of items to process
            context: Shared context dictionary passed to each function call

        Returns:
            list of results from function calls
        """
        if not items:
            return []

        results: list[R] = []
        errors: list[tuple[T, Exception]] = []
        semaphore = await self._get_semaphore()

        async def process_item(item: T) -> None:
            async with semaphore:
                try:
                    result = await func(item, context)
                    if result is not None:
                        results.append(result)
                except OPERATIONAL_EXCEPTIONS as e:
                    if self.error_strategy == ErrorStrategy.RAISE:
                        raise
                    errors.append((item, cast(Exception, e)))
                    self._logger.error(f"Error processing item {item}: {e}")

        try:
            if self.timeout:
                with anyio.fail_after(self.timeout):
                    async with anyio.create_task_group() as tg:
                        for item in items:
                            tg.start_soon(process_item, item)
            else:
                async with anyio.create_task_group() as tg:
                    for item in items:
                        tg.start_soon(process_item, item)
        except TimeoutError:
            self._logger.warning(f"Batch execution timed out after {self.timeout}s")
            if self.error_strategy == ErrorStrategy.RAISE:
                raise

        if errors:
            self._logger.warning(f"Failed to process {len(errors)} items out of {len(items)}")

        return results

    async def execute_mapped_batch(
        self,
        func_map: dict[Any, Callable[[Any], Awaitable[R]]],
        items: list[Any],
        default_func: Callable[[Any], Awaitable[R]] | None = None,
    ) -> list[R]:
        """Execute different async functions based on item type/key in parallel.

        Args:
            func_map: Dictionary mapping item keys/types to async functions
            items: List of items to process
            default_func: Default async function if item not found in func_map

        Returns:
            List of results from the function calls
        """
        if not items:
            return []

        results: list[R] = []
        errors: list[tuple[Any, Exception]] = []
        semaphore = await self._get_semaphore()

        async def process_item(item: Any) -> None:
            # Determine which function to use
            func: Callable[[Any], Awaitable[R]] | None = None
            if hasattr(item, "__class__"):
                func = func_map.get(type(item))
            if func is None:
                func = func_map.get(item)
            if func is None and default_func:
                func = default_func

            if func is None:
                self._logger.warning(f"No function found for item: {item}")
                return

            async with semaphore:
                try:
                    result = await func(item)
                    if result is not None:
                        results.append(result)
                except OPERATIONAL_EXCEPTIONS as e:
                    if self.error_strategy == ErrorStrategy.RAISE:
                        raise
                    errors.append((item, cast(Exception, e)))
                    self._logger.error(f"Error processing item {item}: {e}")

        try:
            if self.timeout:
                with anyio.fail_after(self.timeout):
                    async with anyio.create_task_group() as tg:
                        for item in items:
                            tg.start_soon(process_item, item)
            else:
                async with anyio.create_task_group() as tg:
                    for item in items:
                        tg.start_soon(process_item, item)
        except TimeoutError:
            self._logger.warning(f"Batch execution timed out after {self.timeout}s")
            if self.error_strategy == ErrorStrategy.RAISE:
                raise

        if errors:
            self._logger.warning(f"Failed to process {len(errors)} items out of {len(items)}")

        return results

    async def execute_with_progress(
        self,
        func: Callable[[T], Awaitable[R]],
        items: list[T],
        progress_callback: Callable[[int, int], Any] | None = None,
    ) -> list[R]:
        """Execute an async function with progress tracking.

        Args:
            func: Async function to execute for each item
            items: list of items to process
            progress_callback: Optional callback(completed, total) for progress updates

        Returns:
            list of results from function calls
        """
        if not items:
            return []

        results: list[R] = []
        errors: list[tuple[T, Exception]] = []
        completed = 0
        total = len(items)
        semaphore = await self._get_semaphore()
        lock = anyio.Lock()

        async def process_item(item: T) -> None:
            nonlocal completed
            async with semaphore:
                try:
                    result = await func(item)
                    if result is not None:
                        results.append(result)
                except OPERATIONAL_EXCEPTIONS as e:
                    if self.error_strategy == ErrorStrategy.RAISE:
                        raise
                    errors.append((item, cast(Exception, e)))
                    self._logger.error(f"Error processing item {item}: {e}")
                finally:
                    async with lock:
                        completed += 1
                        if progress_callback:
                            progress_callback(completed, total)

        try:
            if self.timeout:
                with anyio.fail_after(self.timeout):
                    async with anyio.create_task_group() as tg:
                        for item in items:
                            tg.start_soon(process_item, item)
            else:
                async with anyio.create_task_group() as tg:
                    for item in items:
                        tg.start_soon(process_item, item)
        except TimeoutError:
            self._logger.warning(f"Batch execution timed out after {self.timeout}s")
            if self.error_strategy == ErrorStrategy.RAISE:
                raise

        if errors:
            self._logger.warning(f"Failed to process {len(errors)} items out of {len(items)}")

        return results

    async def execute_batch_detailed(
        self,
        func: Callable[[T], Awaitable[R]],
        items: list[T],
    ) -> BatchResult[R]:
        """Execute an async function with detailed result tracking.

        This method always returns a BatchResult with both successful
        and failed items, regardless of error_strategy.

        Args:
            func: Async function to execute for each item
            items: list of items to process

        Returns:
            BatchResult containing successful results and failed items with errors
        """
        if not items:
            return BatchResult()

        result = BatchResult[R]()
        semaphore = await self._get_semaphore()

        async def process_item(item: T) -> None:
            async with semaphore:
                try:
                    r = await func(item)
                    if r is not None:
                        result.successful.append(r)
                except OPERATIONAL_EXCEPTIONS as e:
                    result.failed.append((item, cast(Exception, e)))
                    self._logger.error(f"Error processing item {item}: {e}")

        try:
            if self.timeout:
                with anyio.fail_after(self.timeout):
                    async with anyio.create_task_group() as tg:
                        for item in items:
                            tg.start_soon(process_item, item)
            else:
                async with anyio.create_task_group() as tg:
                    for item in items:
                        tg.start_soon(process_item, item)
        except TimeoutError:
            self._logger.warning(f"Batch execution timed out after {self.timeout}s")

        return result

    def get_stats(self) -> dict[str, Any]:
        """Get executor statistics.

        Returns:
            Dictionary containing executor statistics
        """
        return {
            "max_concurrent": self.max_concurrent,
            "timeout": self.timeout,
            "error_strategy": self.error_strategy.value,
        }


# Global instance for singleton pattern
_async_parallel_executor: AsyncParallelExecutor | None = None


def get_async_parallel_executor(
    max_concurrent: int = 10,
    timeout: float | None = None,
    error_strategy: ErrorStrategy = ErrorStrategy.IGNORE,
) -> AsyncParallelExecutor:
    """Get a configured async parallel executor instance.

    Args:
        max_concurrent: Maximum concurrent operations
        timeout: Timeout for batch operations (optional)
        error_strategy: How to handle errors during execution

    Returns:
        AsyncParallelExecutor: Configured async parallel executor instance
    """
    global _async_parallel_executor
    if _async_parallel_executor is None:
        _async_parallel_executor = AsyncParallelExecutor(
            max_concurrent=max_concurrent,
            timeout=timeout,
            error_strategy=error_strategy,
        )
    return _async_parallel_executor


def create_async_parallel_executor(
    max_concurrent: int = 10,
    timeout: float | None = None,
    error_strategy: ErrorStrategy = ErrorStrategy.IGNORE,
) -> AsyncParallelExecutor:
    """Create a new async parallel executor instance (not singleton).

    Args:
        max_concurrent: Maximum concurrent operations
        timeout: Timeout for batch operations (optional)
        error_strategy: How to handle errors during execution

    Returns:
        AsyncParallelExecutor: New async parallel executor instance
    """
    return AsyncParallelExecutor(
        max_concurrent=max_concurrent,
        timeout=timeout,
        error_strategy=error_strategy,
    )
