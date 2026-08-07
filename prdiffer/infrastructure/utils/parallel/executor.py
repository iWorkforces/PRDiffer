"""Async parallel executor using anyio task groups.

This module provides a native async parallel executor that replaces
ThreadPoolExecutor with anyio's structured concurrency primitives.
"""

import logging
from collections.abc import Callable, Awaitable
from typing import Any, TypeVar

import anyio
from prdiffer.infrastructure.logging.console_logger import get_logger, ConsoleLogger
from prdiffer.infrastructure.utils.parallel.results import (
    BatchResult,
    ErrorStrategy,
    IndexedBatchError,
    IndexedBatchResult,
    IndexedItemOutcome,
)

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
K = TypeVar("K")


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
        logger: logging.Logger | ConsoleLogger | None = None,
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
        errors: list[tuple[T, BaseException]] = []
        semaphore = anyio.Semaphore(self.max_concurrent)

        async def process_item(item: T) -> None:
            async with semaphore:
                try:
                    result = await func(item)
                    if result is not None:
                        results.append(result)
                except OPERATIONAL_EXCEPTIONS as e:
                    if self.error_strategy == ErrorStrategy.RAISE:
                        raise
                    errors.append((item, e))
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
        errors: list[tuple[T, BaseException]] = []
        semaphore = anyio.Semaphore(self.max_concurrent)

        async def process_item(item: T) -> None:
            async with semaphore:
                try:
                    result = await func(item, context)
                    if result is not None:
                        results.append(result)
                except OPERATIONAL_EXCEPTIONS as e:
                    if self.error_strategy == ErrorStrategy.RAISE:
                        raise
                    errors.append((item, e))
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
        errors: list[tuple[Any, BaseException]] = []
        semaphore = anyio.Semaphore(self.max_concurrent)

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
                    errors.append((item, e))
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
        errors: list[tuple[T, BaseException]] = []
        completed = 0
        total = len(items)
        semaphore = anyio.Semaphore(self.max_concurrent)
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
                    errors.append((item, e))
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
    ) -> BatchResult[R, T]:
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
            return BatchResult[R, T]()

        result = BatchResult[R, T]()
        semaphore = anyio.Semaphore(self.max_concurrent)

        async def process_item(item: T) -> None:
            async with semaphore:
                try:
                    r = await func(item)
                    if r is not None:
                        result.successful.append(r)
                except OPERATIONAL_EXCEPTIONS as e:
                    result.failed.append((item, e))
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

    async def execute_indexed_batch(
        self,
        func: Callable[[K], Awaitable[R]],
        items: list[K],
        *,
        strict: bool = True,
        keys: list[K] | None = None,
    ) -> IndexedBatchResult[K, R]:
        """Execute items with identity-preserving indexed results.

        Outcomes are stored by submission index and always returned in input
        order. Strict mode cancels siblings on the first failure and raises
        ``IndexedBatchError`` carrying the full ordered outcome tuple — never a
        compacted success list.

        Args:
            func: Async function applied to each item (or key when ``keys`` given)
            items: Submitted work items (identity when keys is None)
            strict: When True, cancel siblings and raise on first failure
            keys: Optional explicit identity keys parallel to ``items``

        Returns:
            IndexedBatchResult with one outcome per submitted item in order

        Raises:
            ValueError: If keys length mismatches items or keys contain duplicates
            IndexedBatchError: Strict mode failure (includes failed item identity)
            TimeoutError: When batch timeout elapses and strict/raise semantics apply
        """
        if keys is not None and len(keys) != len(items):
            raise ValueError("keys length must match items length")
        identity_keys: list[K] = list(keys) if keys is not None else list(items)
        if len(identity_keys) != len(set(identity_keys)):
            raise ValueError("indexed batch keys must be unique")

        if not items:
            return IndexedBatchResult(outcomes=())

        slot_count = len(items)
        outcomes: list[IndexedItemOutcome[K, R] | None] = [None] * slot_count
        semaphore = anyio.Semaphore(self.max_concurrent)
        cancel_scope_box: dict[str, anyio.CancelScope | None] = {"scope": None}

        async def process_indexed(index: int, item: K, key: K) -> None:
            async with semaphore:
                try:
                    value = await func(item)
                    outcomes[index] = IndexedItemOutcome(index=index, key=key, value=value, error=None)
                except BaseException as exc:  # capture identity even for non-operational errors
                    outcomes[index] = IndexedItemOutcome(index=index, key=key, value=None, error=exc)
                    self._logger.error(
                        "Indexed batch item failed",
                        extra={"index": index, "key": repr(key), "error": str(exc)},
                    )
                    if strict and cancel_scope_box["scope"] is not None:
                        cancel_scope_box["scope"].cancel()
                    if strict:
                        raise

        async def run_all() -> None:
            with anyio.CancelScope() as scope:
                cancel_scope_box["scope"] = scope
                async with anyio.create_task_group() as tg:
                    for index, (item, key) in enumerate(zip(items, identity_keys, strict=True)):
                        tg.start_soon(process_indexed, index, item, key)

        try:
            if self.timeout:
                with anyio.fail_after(self.timeout):
                    await run_all()
            else:
                await run_all()
        except TimeoutError:
            self._logger.warning(f"Indexed batch timed out after {self.timeout}s")
            for index, key in enumerate(identity_keys):
                if outcomes[index] is None:
                    outcomes[index] = IndexedItemOutcome(
                        index=index,
                        key=key,
                        value=None,
                        error=TimeoutError(f"Item timed out after {self.timeout}s"),
                    )
            if strict:
                sealed = tuple(
                    outcome if outcome is not None else IndexedItemOutcome(index=i, key=identity_keys[i], error=RuntimeError("missing outcome"))
                    for i, outcome in enumerate(outcomes)
                )
                raise IndexedBatchError(
                    f"Indexed batch timed out after {self.timeout}s",
                    outcomes=sealed,
                ) from None
        except BaseException as exc:
            # Ensure every slot has an outcome even after cancellation.
            for index, key in enumerate(identity_keys):
                if outcomes[index] is None:
                    outcomes[index] = IndexedItemOutcome(
                        index=index,
                        key=key,
                        value=None,
                        error=exc if strict else RuntimeError("cancelled sibling"),
                    )
            sealed = tuple(
                outcome if outcome is not None else IndexedItemOutcome(index=i, key=identity_keys[i], error=RuntimeError("missing outcome"))
                for i, outcome in enumerate(outcomes)
            )
            if strict:
                # Single failure-selection algorithm: IndexedBatchError.first_failure only.
                provisional = IndexedBatchError(
                    "Indexed batch failed",
                    outcomes=sealed,
                )
                first = provisional.first_failure
                identity = first.key if first is not None else None
                raise IndexedBatchError(
                    f"Indexed batch failed for item identity={identity!r}",
                    outcomes=sealed,
                    cause=first.error if first else exc,
                ) from exc
            return IndexedBatchResult(outcomes=sealed)

        sealed_ok = tuple(
            outcome if outcome is not None else IndexedItemOutcome(index=i, key=identity_keys[i], error=RuntimeError("missing outcome"))
            for i, outcome in enumerate(outcomes)
        )
        batch = IndexedBatchResult(outcomes=sealed_ok)
        if strict and not batch.all_succeeded:
            provisional = IndexedBatchError(
                "Indexed batch failed",
                outcomes=sealed_ok,
            )
            first = provisional.first_failure
            assert first is not None
            raise IndexedBatchError(
                f"Indexed batch failed for item identity={first.key!r}",
                outcomes=sealed_ok,
                cause=first.error,
            )
        return batch

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
