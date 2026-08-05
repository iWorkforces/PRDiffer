"""Unit tests for AsyncParallelExecutor component.

Tests the native async parallel execution service using anyio task groups
with semaphore-based concurrency control and multiple error handling strategies.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from prdiffer.infrastructure.utils.parallel.executor import (
    AsyncParallelExecutor,
    get_async_parallel_executor,
    create_async_parallel_executor,
)
from prdiffer.infrastructure.utils.parallel.results import (
    BatchResult,
    ErrorStrategy,
    IndexedBatchError,
    IndexedBatchResult,
)
import anyio


@pytest.mark.unit
class TestAsyncParallelExecutorInitialization:
    """Test suite for AsyncParallelExecutor initialization."""

    def test_initialization_with_defaults(self):
        """Test executor initialization with default values."""
        executor = AsyncParallelExecutor()

        assert executor.max_concurrent == 10
        assert executor.timeout is None
        assert executor.error_strategy == ErrorStrategy.IGNORE

    def test_initialization_with_custom_values(self):
        """Test executor initialization with custom values."""
        executor = AsyncParallelExecutor(
            max_concurrent=20,
            timeout=30.0,
            error_strategy=ErrorStrategy.RAISE,
        )

        assert executor.max_concurrent == 20
        assert executor.timeout == 30.0
        assert executor.error_strategy == ErrorStrategy.RAISE

    def test_initialization_with_logger(self):
        """Test executor initialization with custom logger."""
        mock_logger = Mock()
        executor = AsyncParallelExecutor(logger=mock_logger)

        assert executor._logger == mock_logger

    def test_get_stats(self):
        """Test get_stats returns executor statistics."""
        executor = AsyncParallelExecutor(
            max_concurrent=15,
            timeout=60.0,
            error_strategy=ErrorStrategy.COLLECT,
        )

        stats = executor.get_stats()

        assert stats["max_concurrent"] == 15
        assert stats["timeout"] == 60.0
        assert stats["error_strategy"] == "collect"


@pytest.mark.unit
class TestBatchResult:
    """Test suite for BatchResult dataclass."""

    def test_empty_result(self):
        """Test empty BatchResult."""
        result = BatchResult()

        assert result.total == 0
        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.success_rate == 100.0
        assert result.all_succeeded is True
        assert result.get_errors() == []

    def test_result_with_successful_items(self):
        """Test BatchResult with successful items."""
        result = BatchResult()
        result.successful.extend(["result1", "result2", "result3"])

        assert result.total == 3
        assert result.success_count == 3
        assert result.failure_count == 0
        assert result.success_rate == 100.0
        assert result.all_succeeded is True

    def test_result_with_failed_items(self):
        """Test BatchResult with failed items."""
        result = BatchResult()
        result.successful.append("result1")
        result.failed.append(("item2", ValueError("Error")))

        assert result.total == 2
        assert result.success_count == 1
        assert result.failure_count == 1
        assert result.success_rate == 50.0
        assert result.all_succeeded is False
        assert len(result.get_errors()) == 1

    def test_result_with_mixed_items(self):
        """Test BatchResult with both successful and failed items."""
        result = BatchResult()
        result.successful.extend(["r1", "r2", "r3"])
        result.failed.append(("item4", RuntimeError("fail")))
        result.failed.append(("item5", TypeError("wrong")))

        assert result.total == 5
        assert result.success_count == 3
        assert result.failure_count == 2
        assert result.success_rate == 60.0
        assert result.all_succeeded is False


@pytest.mark.unit
class TestExecuteBatch:
    """Test suite for execute_batch method."""

    @pytest.mark.asyncio
    async def test_execute_batch_empty_list(self):
        """Test execute_batch with empty list."""
        executor = AsyncParallelExecutor()

        async def fake_func(item):
            return item * 2

        result = await executor.execute_batch(fake_func, [])

        assert result == []

    @pytest.mark.asyncio
    async def test_execute_batch_single_item(self):
        """Test execute_batch with single item."""
        executor = AsyncParallelExecutor()

        async def fake_func(item):
            return item * 2

        result = await executor.execute_batch(fake_func, [5])

        assert result == [10]

    @pytest.mark.asyncio
    async def test_execute_batch_multiple_items(self):
        """Test execute_batch with multiple items."""
        executor = AsyncParallelExecutor()

        async def fake_func(item):
            return item * 2

        result = await executor.execute_batch(fake_func, [1, 2, 3, 4, 5])

        assert set(result) == {2, 4, 6, 8, 10}

    @pytest.mark.asyncio
    async def test_execute_batch_with_ignore_strategy(self):
        """Test execute_batch with IGNORE error strategy."""
        executor = AsyncParallelExecutor(error_strategy=ErrorStrategy.IGNORE)

        call_count = {"value": 0}

        async def fake_func(item):
            call_count["value"] += 1
            if item == 3:
                raise ValueError("Invalid item")
            return item * 2

        result = await executor.execute_batch(fake_func, [1, 2, 3, 4, 5])

        # All 5 items should be processed
        assert call_count["value"] == 5
        # Only successful results returned
        assert set(result) == {2, 4, 8, 10}

    @pytest.mark.asyncio
    async def test_execute_batch_with_raise_strategy(self):
        """Test execute_batch with RAISE error strategy."""
        executor = AsyncParallelExecutor(error_strategy=ErrorStrategy.RAISE)

        async def fake_func(item):
            if item == 3:
                raise ValueError("Invalid item")
            return item * 2

        # anyio raises ExceptionGroup for unhandled errors in task group
        with pytest.raises(ExceptionGroup):
            await executor.execute_batch(fake_func, [1, 2, 3, 4, 5])

    @pytest.mark.asyncio
    async def test_execute_batch_with_collect_strategy(self):
        """Test execute_batch with COLLECT error strategy."""
        executor = AsyncParallelExecutor(error_strategy=ErrorStrategy.COLLECT)

        async def fake_func(item):
            if item == 3:
                raise ValueError("Invalid item")
            return item * 2

        result = await executor.execute_batch(fake_func, [1, 2, 3, 4, 5])

        # Only successful results returned (COLLECT doesn't affect return, just logs)
        assert set(result) == {2, 4, 8, 10}

    @pytest.mark.asyncio
    async def test_execute_batch_with_timeout(self):
        """Test execute_batch with timeout protection."""
        executor = AsyncParallelExecutor(timeout=0.1)

        async def slow_func(item):
            await asyncio.sleep(0.2)  # Sleep longer than timeout
            return item

        # With IGNORE strategy, timeout should log warning but not raise
        result = await executor.execute_batch(slow_func, [1, 2])

        # Results may be incomplete due to timeout
        assert isinstance(result, list)


@pytest.mark.unit
class TestExecuteBatchWithContext:
    """Test suite for execute_batch_with_context method."""

    @pytest.mark.asyncio
    async def test_execute_batch_with_context_empty_list(self):
        """Test execute_batch_with_context with empty list."""
        executor = AsyncParallelExecutor()

        async def fake_func(item, context):
            return f"{item}-{context.get('suffix', '')}"

        result = await executor.execute_batch_with_context(fake_func, [], {"suffix": "test"})

        assert result == []

    @pytest.mark.asyncio
    async def test_execute_batch_with_context_shared(self):
        """Test execute_batch_with_context with shared context."""
        executor = AsyncParallelExecutor()

        async def fake_func(item, context):
            return f"{item}-{context['suffix']}"

        result = await executor.execute_batch_with_context(fake_func, [1, 2, 3], {"suffix": "test"})

        assert set(result) == {"1-test", "2-test", "3-test"}

    @pytest.mark.asyncio
    async def test_execute_batch_with_context_mutable_state(self):
        """Test execute_batch_with_context with mutable context state."""
        executor = AsyncParallelExecutor()
        context = {"counter": 0}

        async def fake_func(item, context):
            context["counter"] += 1
            return f"{item}-{context['counter']}"

        result = await executor.execute_batch_with_context(fake_func, [1, 2, 3], context)

        # Check context was modified
        assert context["counter"] == 3
        # Check results
        assert len(result) == 3


@pytest.mark.unit
class TestExecuteMappedBatch:
    """Test suite for execute_mapped_batch method."""

    @pytest.mark.asyncio
    async def test_execute_mapped_batch_empty_list(self):
        """Test execute_mapped_batch with empty list."""
        executor = AsyncParallelExecutor()

        func_map = {
            "type1": AsyncMock(return_value="result1"),
            "type2": AsyncMock(return_value="result2"),
        }

        result = await executor.execute_mapped_batch(func_map, [])

        assert result == []

    @pytest.mark.asyncio
    async def test_execute_mapped_batch_with_string_keys(self):
        """Test execute_mapped_batch with string keys."""
        executor = AsyncParallelExecutor()

        async def func1(item):
            return f"func1-{item}"

        async def func2(item):
            return f"func2-{item}"

        func_map = {"a": func1, "b": func2}

        result = await executor.execute_mapped_batch(func_map, ["a", "b", "a"])

        assert set(result) == {"func1-a", "func2-b"}

    @pytest.mark.asyncio
    async def test_execute_mapped_batch_with_default_func(self):
        """Test execute_mapped_batch with default function."""
        executor = AsyncParallelExecutor()

        async def special_func(item):
            return f"special-{item}"

        async def default_func(item):
            return f"default-{item}"

        func_map = {"special": special_func}

        result = await executor.execute_mapped_batch(func_map, ["special", "other"], default_func=default_func)

        assert set(result) == {"special-special", "default-other"}

    @pytest.mark.asyncio
    async def test_execute_mapped_batch_no_matching_function(self):
        """Test execute_mapped_batch with no matching function."""
        executor = AsyncParallelExecutor()

        func_map = {"type1": AsyncMock(return_value="result1")}

        result = await executor.execute_mapped_batch(func_map, ["type2"], default_func=None)

        # No function for type2, so empty result
        assert result == []


@pytest.mark.unit
class TestExecuteWithProgress:
    """Test suite for execute_with_progress method."""

    @pytest.mark.asyncio
    async def test_execute_with_progress_empty_list(self):
        """Test execute_with_progress with empty list."""
        executor = AsyncParallelExecutor()

        progress_calls = []

        async def fake_func(item):
            return item * 2

        async def progress_callback(completed, total):
            progress_calls.append((completed, total))

        result = await executor.execute_with_progress(fake_func, [], progress_callback)

        assert result == []
        assert progress_calls == []

    @pytest.mark.asyncio
    async def test_execute_with_progress_calls_callback(self):
        """Test execute_with_progress calls progress callback."""
        executor = AsyncParallelExecutor()

        progress_calls = []

        async def fake_func(item):
            return item * 2

        # Note: callback must be sync, not async (implementation doesn't await it)
        def progress_callback(completed, total):
            progress_calls.append((completed, total))

        result = await executor.execute_with_progress(fake_func, [1, 2, 3, 4, 5], progress_callback)

        # Check results
        assert set(result) == {2, 4, 6, 8, 10}

        # Check progress was reported
        assert len(progress_calls) == 5
        # Final call should show all complete
        assert progress_calls[-1] == (5, 5)

    @pytest.mark.asyncio
    async def test_execute_with_progress_without_callback(self):
        """Test execute_with_progress without callback works."""
        executor = AsyncParallelExecutor()

        async def fake_func(item):
            return item * 2

        result = await executor.execute_with_progress(fake_func, [1, 2, 3])

        assert set(result) == {2, 4, 6}

    @pytest.mark.asyncio
    async def test_execute_with_progress_with_errors(self):
        """Test execute_with_progress reports progress even with errors."""
        executor = AsyncParallelExecutor(error_strategy=ErrorStrategy.IGNORE)

        progress_calls = []

        async def fake_func(item):
            if item == 2:
                raise ValueError("Error")
            return item * 2

        # Note: callback must be sync, not async (implementation doesn't await it)
        def progress_callback(completed, total):
            progress_calls.append((completed, total))

        _ = await executor.execute_with_progress(fake_func, [1, 2, 3, 4, 5], progress_callback)

        # Progress should still be reported for all items
        assert len(progress_calls) == 5
        # Final call should show all complete
        assert progress_calls[-1] == (5, 5)


@pytest.mark.unit
class TestExecuteBatchDetailed:
    """Test suite for execute_batch_detailed method."""

    @pytest.mark.asyncio
    async def test_execute_batch_detailed_empty_list(self):
        """Test execute_batch_detailed with empty list."""
        executor = AsyncParallelExecutor()

        async def fake_func(item):
            return item * 2

        result = await executor.execute_batch_detailed(fake_func, [])

        assert isinstance(result, BatchResult)
        assert result.total == 0
        assert result.all_succeeded is True

    @pytest.mark.asyncio
    async def test_execute_batch_detailed_all_success(self):
        """Test execute_batch_detailed with all successful."""
        executor = AsyncParallelExecutor()

        async def fake_func(item):
            return item * 2

        result = await executor.execute_batch_detailed(fake_func, [1, 2, 3])

        assert isinstance(result, BatchResult)
        assert result.total == 3
        assert result.success_count == 3
        assert result.failure_count == 0
        assert result.all_succeeded is True
        assert set(result.successful) == {2, 4, 6}

    @pytest.mark.asyncio
    async def test_execute_batch_detailed_with_failures(self):
        """Test execute_batch_detailed with some failures."""
        executor = AsyncParallelExecutor()

        async def fake_func(item):
            if item == 2:
                raise ValueError("Error on 2")
            if item == 4:
                raise RuntimeError("Error on 4")
            return item * 2

        result = await executor.execute_batch_detailed(fake_func, [1, 2, 3, 4, 5])

        assert isinstance(result, BatchResult)
        assert result.total == 5
        assert result.success_count == 3
        assert result.failure_count == 2
        assert result.all_succeeded is False
        assert set(result.successful) == {2, 6, 10}
        assert len(result.failed) == 2

    @pytest.mark.asyncio
    async def test_execute_batch_detailed_with_none_returns(self):
        """Test execute_batch_detailed filters out None returns."""
        executor = AsyncParallelExecutor()

        async def fake_func(item):
            if item % 2 == 0:
                return None
            return item * 2

        result = await executor.execute_batch_detailed(fake_func, [1, 2, 3, 4, 5])

        # None results are filtered from successful
        assert result.success_count == 3
        assert set(result.successful) == {2, 6, 10}


@pytest.mark.unit
class TestConcurrencyControl:
    """Test suite for concurrency control with semaphore."""

    @pytest.mark.asyncio
    async def test_max_concurrent_is_respected(self):
        """Test that max_concurrent limits concurrent execution."""
        executor = AsyncParallelExecutor(max_concurrent=2)

        active_count = {"value": 0}
        max_active = {"value": 0}

        async def fake_func(item):
            active_count["value"] += 1
            max_active["value"] = max(max_active["value"], active_count["value"])

            await asyncio.sleep(0.05)  # Simulate work

            active_count["value"] -= 1
            return item

        await executor.execute_batch(fake_func, [1, 2, 3, 4, 5])

        # Max concurrent should not exceed 2
        assert max_active["value"] <= 2

    @pytest.mark.asyncio
    async def test_semaphore_reuse(self):
        """Test that semaphore is reused across calls."""
        executor = AsyncParallelExecutor(max_concurrent=2)

        async def fake_func(item):
            return item

        # First call creates semaphore
        await executor.execute_batch(fake_func, [1, 2])

        semaphore1 = await executor._get_semaphore()

        # Second call should reuse same semaphore
        await executor.execute_batch(fake_func, [3, 4])

        semaphore2 = await executor._get_semaphore()

        assert semaphore1 is semaphore2


@pytest.mark.unit
class TestTimeoutHandling:
    """Test suite for timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_with_raise_strategy(self):
        """Test timeout with RAISE error strategy raises TimeoutError."""
        executor = AsyncParallelExecutor(timeout=0.1, error_strategy=ErrorStrategy.RAISE)

        async def slow_func(item):
            await asyncio.sleep(0.5)
            return item

        # Timeout should raise with RAISE strategy
        with pytest.raises(TimeoutError):
            await executor.execute_batch(slow_func, [1, 2])

    @pytest.mark.asyncio
    async def test_timeout_with_ignore_strategy(self):
        """Test timeout with IGNORE error strategy doesn't raise."""
        executor = AsyncParallelExecutor(timeout=0.1, error_strategy=ErrorStrategy.IGNORE)

        async def slow_func(item):
            await asyncio.sleep(0.5)
            return item

        # Timeout should not raise with IGNORE strategy
        result = await executor.execute_batch(slow_func, [1, 2])

        # Results may be partial or empty
        assert isinstance(result, list)


@pytest.mark.unit
class TestFactoryFunctions:
    """Test suite for factory functions."""

    def test_create_async_parallel_executor(self):
        """Test create_async_parallel_executor creates new instance."""
        executor1 = create_async_parallel_executor(max_concurrent=5)
        executor2 = create_async_parallel_executor(max_concurrent=10)

        assert executor1 is not executor2
        assert executor1.max_concurrent == 5
        assert executor2.max_concurrent == 10

    def test_get_async_parallel_executor_singleton(self):
        """Test get_async_parallel_executor returns singleton."""
        # Reset the global singleton
        import prdiffer.infrastructure.utils.parallel.executor as executor_module

        executor_module._async_parallel_executor = None

        executor1 = get_async_parallel_executor(max_concurrent=5)
        executor2 = get_async_parallel_executor(max_concurrent=10)

        assert executor1 is executor2
        # First call sets the config
        assert executor1.max_concurrent == 5


@pytest.mark.unit
class TestErrorHandlingStrategies:
    """Test suite for error handling strategies."""

    @pytest.mark.asyncio
    async def test_ignore_strategy_continues_on_error(self):
        """Test IGNORE strategy continues processing on errors."""
        executor = AsyncParallelExecutor(error_strategy=ErrorStrategy.IGNORE)

        processed = []

        async def fake_func(item):
            processed.append(item)
            if item == 3:
                raise ValueError("Error")
            return item * 2

        result = await executor.execute_batch(fake_func, [1, 2, 3, 4, 5])

        # All items processed despite errors
        assert set(processed) == {1, 2, 3, 4, 5}
        # Only successful results returned
        assert set(result) == {2, 4, 8, 10}

    @pytest.mark.asyncio
    async def test_raise_strategy_stops_on_error(self):
        """Test RAISE strategy stops processing on first error."""
        executor = AsyncParallelExecutor(error_strategy=ErrorStrategy.RAISE)

        processed = []

        async def fake_func(item):
            processed.append(item)
            if item == 3:
                raise ValueError("Error")
            return item * 2

        # anyio raises ExceptionGroup for unhandled errors in task group
        with pytest.raises(ExceptionGroup):
            await executor.execute_batch(fake_func, [1, 2, 3, 4, 5])

        # Not all items processed (stopped at error)
        # Note: Due to concurrency, some items after 3 might be processed
        assert 3 in processed

    @pytest.mark.asyncio
    async def test_collect_strategy_logs_errors(self):
        """Test COLLECT strategy logs but doesn't raise."""
        executor = AsyncParallelExecutor(error_strategy=ErrorStrategy.COLLECT)

        async def fake_func(item):
            if item == 3:
                raise ValueError("Error")
            return item * 2

        result = await executor.execute_batch(fake_func, [1, 2, 3, 4, 5])

        # Should return results without raising
        assert isinstance(result, list)
        # Only successful results returned
        assert set(result) == {2, 4, 8, 10}

    @pytest.mark.asyncio
    async def test_continue_strategy_processes_all(self):
        """Test CONTINUE strategy processes all items."""
        executor = AsyncParallelExecutor(error_strategy=ErrorStrategy.CONTINUE)

        processed = []

        async def fake_func(item):
            processed.append(item)
            if item == 3:
                raise ValueError("Error")
            return item * 2

        result = await executor.execute_batch(fake_func, [1, 2, 3, 4, 5])

        # All items should be processed
        assert set(processed) == {1, 2, 3, 4, 5}
        # Only successful results returned
        assert set(result) == {2, 4, 8, 10}


@pytest.mark.unit
class TestEdgeCases:
    """Test suite for edge cases."""

    @pytest.mark.asyncio
    async def test_none_results_are_filtered(self):
        """Test that None results are filtered from output."""
        executor = AsyncParallelExecutor()

        async def fake_func(item):
            if item == 2:
                return None
            return item * 2

        result = await executor.execute_batch(fake_func, [1, 2, 3, 4, 5])

        # None results filtered out
        assert set(result) == {2, 6, 8, 10}

    @pytest.mark.asyncio
    async def test_all_none_results(self):
        """Test that all None results returns empty list."""
        executor = AsyncParallelExecutor()

        async def fake_func(item):
            return None

        result = await executor.execute_batch(fake_func, [1, 2, 3])

        assert result == []

    @pytest.mark.asyncio
    async def test_single_item_with_error(self):
        """Test single item that raises an error."""
        executor = AsyncParallelExecutor(error_strategy=ErrorStrategy.IGNORE)

        async def fake_func(item):
            raise ValueError("Error")

        result = await executor.execute_batch(fake_func, [1])

        # Error ignored, empty result
        assert result == []


@pytest.mark.unit
class TestExecuteIndexedBatch:
    """Indexed all-or-error batch contract tests."""

    @pytest.mark.asyncio
    async def test_reverse_completion_preserves_submission_order(self):
        executor = AsyncParallelExecutor(max_concurrent=3, error_strategy=ErrorStrategy.RAISE)
        release = {name: anyio.Event() for name in ("a", "b", "c")}

        async def work(name: str) -> str:
            await release[name].wait()
            return name.upper()

        async def run() -> None:
            # Complete c, then a, then b — result order must still be a,b,c
            async with anyio.create_task_group() as tg:

                async def starter():
                    await anyio.sleep(0.01)
                    release["c"].set()
                    await anyio.sleep(0.01)
                    release["a"].set()
                    await anyio.sleep(0.01)
                    release["b"].set()

                tg.start_soon(starter)
                batch = await executor.execute_indexed_batch(work, ["a", "b", "c"], strict=True)
                assert [o.key for o in batch.outcomes] == ["a", "b", "c"]
                assert list(batch.values_in_order) == ["A", "B", "C"]

        await run()

    @pytest.mark.asyncio
    async def test_failed_middle_item_raises_with_identity(self):
        executor = AsyncParallelExecutor(max_concurrent=3, error_strategy=ErrorStrategy.IGNORE)
        started: list[str] = []
        finished: list[str] = []

        async def work(name: str) -> str:
            started.append(name)
            if name == "b":
                raise ValueError("boom-b")
            await anyio.sleep(0.05)
            finished.append(name)
            return name

        with pytest.raises(IndexedBatchError) as exc_info:
            await executor.execute_indexed_batch(work, ["a", "b", "c"], strict=True)

        err = exc_info.value
        assert err.first_failure is not None
        assert err.first_failure.key == "b"
        assert isinstance(err.first_failure.error, ValueError)
        assert [o.index for o in err.outcomes] == [0, 1, 2]
        # No compacted success list escapes
        with pytest.raises(IndexedBatchError):
            _ = IndexedBatchResult(outcomes=err.outcomes).values_in_order

    @pytest.mark.asyncio
    async def test_duplicate_keys_rejected(self):
        executor = AsyncParallelExecutor(max_concurrent=2)

        async def work(name: str) -> str:
            return name

        with pytest.raises(ValueError, match="unique"):
            await executor.execute_indexed_batch(work, ["a", "a"], strict=True)

    @pytest.mark.asyncio
    async def test_timeout_marks_pending_items(self):
        executor = AsyncParallelExecutor(max_concurrent=2, timeout=0.05)

        async def work(name: str) -> str:
            await anyio.sleep(1.0)
            return name

        with pytest.raises((IndexedBatchError, TimeoutError)):
            await executor.execute_indexed_batch(work, ["a", "b"], strict=True)

    @pytest.mark.asyncio
    async def test_non_strict_collects_failures_in_order(self):
        executor = AsyncParallelExecutor(max_concurrent=3)

        async def work(name: str) -> str:
            if name == "b":
                raise RuntimeError("fail-b")
            return name

        batch = await executor.execute_indexed_batch(work, ["a", "b", "c"], strict=False)
        assert [o.key for o in batch.outcomes] == ["a", "b", "c"]
        assert batch.outcomes[0].ok is True
        assert batch.outcomes[1].ok is False
        assert batch.outcomes[2].ok is True
        assert batch.outcomes[0].value == "a"
        assert batch.outcomes[2].value == "c"

    @pytest.mark.asyncio
    async def test_explicit_keys_parallel_to_items(self):
        executor = AsyncParallelExecutor(max_concurrent=2)

        async def work(item: int) -> int:
            return item * 10

        batch = await executor.execute_indexed_batch(
            work,
            [1, 2, 3],
            keys=["x", "y", "z"],
            strict=True,
        )
        assert [o.key for o in batch.outcomes] == ["x", "y", "z"]
        assert list(batch.values_in_order) == [10, 20, 30]
