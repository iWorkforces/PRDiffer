"""Async parallel execution service using anyio task groups.

This module provides a native async parallel executor that replaces
ThreadPoolExecutor with anyio's structured concurrency primitives.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    List,
    Callable,
    Any,
    Optional,
    Dict,
    TypeVar,
    Awaitable,
    Tuple,
    Generic,
    Type,
    cast,
)
import anyio
from prdiffer.infrastructure.logging.console_logger import get_logger

# Exceptions to catch in parallel execution
# Note: We deliberately exclude KeyboardInterrupt, SystemExit, and GeneratorExit
# to allow system-level exceptions to propagate for proper shutdown/cleanup.
OPERATIONAL_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
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


class ErrorStrategy(str, Enum):
    """Error handling strategy for parallel execution."""

    IGNORE = "ignore"  # Log errors, return only successful results
    RAISE = "raise"  # Raise first exception encountered
    COLLECT = "collect"  # Return both successful results and errors
    CONTINUE = "continue"  # Continue processing, return detailed batch results


@dataclass
class BatchResult(Generic[T]):
    """Result of a batch execution with success/failure tracking."""

    successful: List[T] = field(default_factory=list)
    failed: List[Tuple[Any, Exception]] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of items processed."""
        return len(self.successful) + len(self.failed)

    @property
    def success_count(self) -> int:
        """Number of successful items."""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Number of failed items."""
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if self.total == 0:
            return 100.0
        return (self.success_count / self.total) * 100

    @property
    def all_succeeded(self) -> bool:
        """Check if all items succeeded."""
        return len(self.failed) == 0

    def get_errors(self) -> List[Exception]:
        """Get list of all exceptions."""
        return [error for _, error in self.failed]


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
        timeout: Optional[float] = None,
        error_strategy: ErrorStrategy = ErrorStrategy.IGNORE,
        logger: Optional[Any] = None,
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
        self._semaphore: Optional[anyio.Semaphore] = None

    async def _get_semaphore(self) -> anyio.Semaphore:
        """Get or create the semaphore for concurrency control."""
        if self._semaphore is None:
            self._semaphore = anyio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def execute_batch(
        self,
        func: Callable[[T], Awaitable[R]],
        items: List[T],
    ) -> List[R]:
        """Execute an async function on a list of items in parallel.

        Args:
            func: Async function to execute for each item
            items: List of items to process

        Returns:
            List of results from the function calls (errors filtered based on strategy)

        Raises:
            Exception: If error_strategy is RAISE and any operation fails
        """
        if not items:
            return []

        results: List[R] = []
        errors: List[Tuple[T, Exception]] = []
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
            self._logger.warning(
                f"Failed to process {len(errors)} items out of {len(items)}"
            )

        return results

    async def execute_batch_with_context(
        self,
        func: Callable[[T, Dict[str, Any]], Awaitable[R]],
        items: List[T],
        context: Dict[str, Any],
    ) -> List[R]:
        """Execute an async function on items with shared context in parallel.

        Args:
            func: Async function to execute (accepts item and context)
            items: List of items to process
            context: Shared context dictionary passed to each function call

        Returns:
            List of results from the function calls
        """
        if not items:
            return []

        results: List[R] = []
        errors: List[Tuple[T, Exception]] = []
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
            self._logger.warning(
                f"Failed to process {len(errors)} items out of {len(items)}"
            )

        return results

    async def execute_mapped_batch(
        self,
        func_map: Dict[Any, Callable[[Any], Awaitable[R]]],
        items: List[Any],
        default_func: Optional[Callable[[Any], Awaitable[R]]] = None,
    ) -> List[R]:
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

        results: List[R] = []
        errors: List[Tuple[Any, Exception]] = []
        semaphore = await self._get_semaphore()

        async def process_item(item: Any) -> None:
            # Determine which function to use
            func: Optional[Callable[[Any], Awaitable[R]]] = None
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
            self._logger.warning(
                f"Failed to process {len(errors)} items out of {len(items)}"
            )

        return results

    async def execute_with_progress(
        self,
        func: Callable[[T], Awaitable[R]],
        items: List[T],
        progress_callback: Optional[Callable[[int, int], Any]] = None,
    ) -> List[R]:
        """Execute an async function with progress tracking.

        Args:
            func: Async function to execute for each item
            items: List of items to process
            progress_callback: Optional callback(completed, total) for progress updates

        Returns:
            List of results from the function calls
        """
        if not items:
            return []

        results: List[R] = []
        errors: List[Tuple[T, Exception]] = []
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
            self._logger.warning(
                f"Failed to process {len(errors)} items out of {len(items)}"
            )

        return results

    async def execute_batch_detailed(
        self,
        func: Callable[[T], Awaitable[R]],
        items: List[T],
    ) -> BatchResult[R]:
        """Execute an async function with detailed result tracking.

        This method always returns a BatchResult with both successful
        and failed items, regardless of error_strategy.

        Args:
            func: Async function to execute for each item
            items: List of items to process

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

    def get_stats(self) -> Dict[str, Any]:
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
_async_parallel_executor: Optional[AsyncParallelExecutor] = None


def get_async_parallel_executor(
    max_concurrent: int = 10,
    timeout: Optional[float] = None,
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
    timeout: Optional[float] = None,
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
