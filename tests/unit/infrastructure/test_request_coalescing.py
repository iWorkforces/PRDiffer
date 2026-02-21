"""Unit tests for RequestCoalescingService.

Tests RequestCoalescingService which deduplicates concurrent requests
for the same resource to prevent duplicate API calls.
"""

import pytest
import anyio

from prdiffer.infrastructure.utils.coalescing import (
    RequestCoalescingService,
    CoalescedRequest,
    DEFAULT_MAX_WAITERS,
)


class TestRequestCoalescingServiceInitialization:
    """Test suite for RequestCoalescingService initialization."""

    def test_initialization_without_logger(self):
        """Test that RequestCoalescingService can be initialized without logger."""
        service = RequestCoalescingService()

        assert service is not None
        assert hasattr(service, '_pending_requests')
        assert hasattr(service, '_lock')
        assert service._max_waiters == DEFAULT_MAX_WAITERS

    def test_initialization_with_custom_max_waiters(self):
        """Test that custom max_waiters is accepted."""
        custom_max = 50
        service = RequestCoalescingService(max_waiters=custom_max)

        assert service._max_waiters == custom_max

    def test_initialization_empty_pending_requests(self):
        """Test that service starts with empty pending requests."""
        service = RequestCoalescingService()

        assert len(service._pending_requests) == 0


class TestRequestCoalescingServiceCoalesceSingleRequest:
    """Test suite for coalesce method with single request."""

    @pytest.mark.asyncio
    async def test_coalesce_single_request(self):
        """Test that single request executes fetch function normally."""
        service = RequestCoalescingService()

        fetch_called = []

        async def mock_fetch():
            fetch_called.append(True)
            return 'result'

        result = await service.coalesce('key1', mock_fetch)

        assert result == 'result'
        assert len(fetch_called) == 1
        assert len(service._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_coalesce_returns_fetch_result(self):
        """Test that coalesce returns the result from fetch function."""
        service = RequestCoalescingService()

        expected_result = {'data': 'test'}

        async def mock_fetch():
            return expected_result

        result = await service.coalesce('key1', mock_fetch)

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_coalesce_removes_pending_request_after_completion(self):
        """Test that pending request is cleaned up after completion."""
        service = RequestCoalescingService()

        async def mock_fetch():
            return 'done'

        await service.coalesce('key1', mock_fetch)

        assert 'key1' not in service._pending_requests


class TestRequestCoalescingServiceCoalesceConcurrentRequests:
    """Test suite for coalesce method with concurrent requests."""

    @pytest.mark.asyncio
    async def test_coalesce_two_concurrent_requests(self):
        """Test that two concurrent requests are coalesced into one."""
        service = RequestCoalescingService()

        fetch_count = []

        async def mock_fetch():
            fetch_count.append(1)
            await anyio.sleep(0.1)
            return 'shared_result'

        results = [None, None]
        async with anyio.create_task_group() as tg:
            for i in range(2):

                async def capture_result(idx=i):
                    results[idx] = await service.coalesce('key1', mock_fetch)

                tg.start_soon(capture_result)

        assert len(fetch_count) == 1
        assert results == ['shared_result', 'shared_result']

    @pytest.mark.asyncio
    async def test_coalesce_three_concurrent_requests(self):
        """Test that three concurrent requests share one fetch."""
        service = RequestCoalescingService()

        fetch_count = []

        async def mock_fetch():
            fetch_count.append(1)
            await anyio.sleep(0.1)
            return 'shared_result'

        results = [None, None, None]
        async with anyio.create_task_group() as tg:
            for i in range(3):

                async def capture_result(idx=i):
                    results[idx] = await service.coalesce('key1', mock_fetch)

                tg.start_soon(capture_result)

        assert len(fetch_count) == 1
        assert all(r == 'shared_result' for r in results)

    @pytest.mark.asyncio
    async def test_coalesce_different_keys_execute_separately(self):
        """Test that different keys execute separately."""
        service = RequestCoalescingService()

        fetch_count = {'key1': 0, 'key2': 0}

        async def mock_fetch_key1():
            fetch_count['key1'] += 1
            await anyio.sleep(0.05)
            return 'result_key1'

        async def mock_fetch_key2():
            fetch_count['key2'] += 1
            await anyio.sleep(0.05)
            return 'result_key2'

        results = [None, None]
        async with anyio.create_task_group() as tg:

            async def capture_key1():
                results[0] = await service.coalesce('key1', mock_fetch_key1)

            async def capture_key2():
                results[1] = await service.coalesce('key2', mock_fetch_key2)

            tg.start_soon(capture_key1)
            tg.start_soon(capture_key2)

        # Each key should trigger its own fetch
        assert fetch_count['key1'] == 1
        assert fetch_count['key2'] == 1
        assert results[0] == 'result_key1'
        assert results[1] == 'result_key2'

    @pytest.mark.asyncio
    async def test_coalesce_waits_in_flight_request(self):
        """Test that later requests wait for in-flight request."""
        service = RequestCoalescingService()
        execution_order = []

        async def mock_fetch():
            execution_order.append('fetch')
            await anyio.sleep(0.1)
            return 'result'

        async def delayed_request(key):
            await anyio.sleep(0.01)
            return await service.coalesce(key, mock_fetch)

        results = [None, None]
        async with anyio.create_task_group() as tg:

            async def capture_key1():
                results[0] = await delayed_request('key1')

            async def capture_key2():
                results[1] = await delayed_request('key2')

            tg.start_soon(capture_key1)
            tg.start_soon(capture_key2)

        assert len(execution_order) == 2
        assert results == ['result', 'result']


class TestRequestCoalescingServiceCoalesceExceptionHandling:
    """Test suite for coalesce exception handling."""

    @pytest.mark.asyncio
    async def test_coalesce_propagates_exception(self):
        """Test that exceptions are propagated to all waiters."""
        service = RequestCoalescingService()

        async def mock_fetch():
            raise ValueError('Test error')

        exceptions_caught = []
        async with anyio.create_task_group() as tg:

            async def capture_exception():
                try:
                    await service.coalesce('key1', mock_fetch)
                except ValueError as e:
                    exceptions_caught.append(e)

            tg.start_soon(capture_exception)
            tg.start_soon(capture_exception)

        assert len(exceptions_caught) == 2
        assert all('Test error' in str(e) for e in exceptions_caught)

    @pytest.mark.asyncio
    async def test_coalesce_exception_propagates_to_all_waiters(self):
        """Test that exception is propagated to all concurrent waiters."""
        service = RequestCoalescingService(max_waiters=10)

        async def mock_fetch():
            raise RuntimeError('Simulated failure')

        exceptions_caught = []

        async def wait_for_error():
            try:
                await service.coalesce('key1', mock_fetch)
            except RuntimeError as e:
                exceptions_caught.append(str(e))

        async with anyio.create_task_group() as tg:
            for _ in range(5):
                tg.start_soon(wait_for_error)

        assert len(exceptions_caught) == 5

    @pytest.mark.asyncio
    async def test_coalesce_cleanup_on_exception(self):
        """Test that pending request is cleaned up on exception."""
        service = RequestCoalescingService()

        async def mock_fetch():
            raise ValueError('Test error')

        with pytest.raises(ValueError):
            await service.coalesce('key1', mock_fetch)

        assert 'key1' not in service._pending_requests


class TestRequestCoalescingServiceCoalesceTimeout:
    """Test suite for coalesce timeout handling."""

    @pytest.mark.asyncio
    async def test_coalesce_timeout_raises_timeout_error(self):
        """Test that timeout raises TimeoutError."""
        service = RequestCoalescingService()

        async def mock_fetch():
            await anyio.sleep(0.2)
            return 'result'

        with pytest.raises(TimeoutError):
            await service.coalesce('key1', mock_fetch, timeout=0.05)

    @pytest.mark.asyncio
    async def test_coalesce_timeout_with_default_timeout(self):
        """Test that default timeout of 30 seconds works."""
        service = RequestCoalescingService()

        async def mock_fetch():
            await anyio.sleep(0.01)
            return 'result'

        result = await service.coalesce('key1', mock_fetch)

        assert result == 'result'

    @pytest.mark.asyncio
    async def test_coalesce_timeout_propagates_to_waiters(self):
        """Test that timeout error propagates to waiting requests."""
        service = RequestCoalescingService()

        async def mock_fetch():
            await anyio.sleep(0.3)

        exceptions_caught = []
        async with anyio.create_task_group() as tg:

            async def capture_timeout():
                try:
                    await service.coalesce('key1', mock_fetch, timeout=0.1)
                except TimeoutError:
                    exceptions_caught.append(True)

            tg.start_soon(capture_timeout)
            tg.start_soon(capture_timeout)

        assert len(exceptions_caught) == 2


class TestRequestCoalescingServiceMaxWaiters:
    """Test suite for maximum waiter limit enforcement."""

    @pytest.mark.asyncio
    async def test_coalesce_respects_max_waiters_limit(self):
        """Test that max_waiters limit triggers new request execution."""
        service = RequestCoalescingService(max_waiters=3)

        fetch_count = []

        async def mock_fetch():
            fetch_count.append(1)
            await anyio.sleep(0.05)
            return 'result'

        async def make_request(key):
            return await service.coalesce(key, mock_fetch)

        # With 4 concurrent requests and max_waiters=3,
        # at least one should start a new request
        results = [None] * 4
        async with anyio.create_task_group() as tg:
            for i in range(4):

                async def capture_result(idx=i):
                    results[idx] = await make_request('key1')

                tg.start_soon(capture_result)

        # At least 2 fetches should have been made (due to max_waiters limit)
        assert len(fetch_count) >= 2
        assert all(r == 'result' for r in results)

    @pytest.mark.asyncio
    async def test_coalesce_exceeds_limit_executes_new_request(self):
        """Test that exceeding limit executes new request instead of waiting."""
        service = RequestCoalescingService(max_waiters=3)

        fetch_count = []

        async def mock_fetch():
            fetch_count.append(1)
            await anyio.sleep(0.05)
            return f'result_{len(fetch_count)}'

        results = [None] * 5
        async with anyio.create_task_group() as tg:
            for i in range(5):

                async def capture_result(idx=i):
                    results[idx] = await service.coalesce('key1', mock_fetch)

                tg.start_soon(capture_result)

        # At least 2 fetches should have been made (due to max_waiters limit)
        assert len(fetch_count) >= 2
        # All results should have been captured
        assert all(r is not None for r in results)


class TestRequestCoalescingServiceClear:
    """Test suite for clear method."""

    @pytest.mark.asyncio
    async def test_clear_removes_all_pending_requests(self):
        """Test that clear removes all pending requests."""
        service = RequestCoalescingService()

        async def mock_fetch():
            await anyio.sleep(0.01)
            return 'result'

        # Complete the requests first
        await service.coalesce('key1', mock_fetch)
        await service.coalesce('key2', mock_fetch)

        # Clear should work on async method
        await service.clear()

        assert len(service._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_clear_can_be_called_when_empty(self):
        """Test that clear works when no pending requests."""
        service = RequestCoalescingService()

        # Clear is an async method
        await service.clear()

        assert len(service._pending_requests) == 0


class TestRequestCoalescingServiceGetStats:
    """Test suite for get_stats method."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_dict(self):
        """Test that get_stats returns a dictionary."""
        service = RequestCoalescingService()

        async def mock_fetch():
            return 'result'

        await service.coalesce('key1', mock_fetch)

        stats = await service.get_stats()

        assert isinstance(stats, dict)
        assert 'pending_count' in stats
        assert 'pending_keys' in stats
        assert 'total_waiters' in stats

    @pytest.mark.asyncio
    async def test_get_stats_correct_counts_after_completion(self):
        """Test that get_stats shows zero after requests complete."""
        service = RequestCoalescingService()

        async def mock_fetch():
            return 'result'

        # Complete requests - they will be removed from pending after completion
        await service.coalesce('key1', mock_fetch)
        await service.coalesce('key2', mock_fetch)

        stats = await service.get_stats()

        # After completion, pending should be 0
        assert stats['pending_count'] == 0
        assert stats['total_waiters'] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_concurrent_requests(self):
        """Test that get_stats counts concurrent waiters correctly during execution."""
        service = RequestCoalescingService()

        async def mock_fetch():
            # Sleep to ensure we can capture stats while request is in-flight
            await anyio.sleep(0.2)
            return 'result'

        stats_during = None
        results = [None] * 3

        async def capture_result(idx):
            results[idx] = await service.coalesce('key1', mock_fetch)

        async def capture_stats():
            nonlocal stats_during
            # Small delay to ensure the request has started
            await anyio.sleep(0.05)
            stats_during = await service.get_stats()

        async with anyio.create_task_group() as tg:
            for i in range(3):
                tg.start_soon(capture_result, i)
            tg.start_soon(capture_stats)

        # During execution, we should have 1 pending key with 3 waiters
        assert stats_during is not None
        assert stats_during['pending_count'] == 1
        assert stats_during['total_waiters'] == 3


class TestCoalescedRequest:
    """Test suite for CoalescedRequest data class."""

    def test_coalesced_request_initialization(self):
        """Test that CoalescedRequest can be initialized."""
        request = CoalescedRequest(key='test_key')

        assert request.key == 'test_key'
        assert request.event.is_set() is False
        assert request.result is None
        assert request.exception is None
        assert request.request_count == 1

    def test_coalesced_request_with_event(self):
        """Test that event can be set."""
        request = CoalescedRequest(key='test_key')

        request.event.set()

        assert request.event.is_set() is True

    def test_coalesced_request_with_result(self):
        """Test that result can be set."""
        request = CoalescedRequest(key='test_key')

        request.result = 'test_result'

        assert request.result == 'test_result'

    def test_coalesced_request_with_exception(self):
        """Test that exception can be set."""
        request = CoalescedRequest(key='test_key')

        request.exception = ValueError('Test error')

        assert request.exception is not None
        assert isinstance(request.exception, ValueError)

    def test_coalesced_request_with_multiple_waiters(self):
        """Test that request count increments."""
        request = CoalescedRequest(key='test_key')

        assert request.request_count == 1

        request.request_count += 1
        assert request.request_count == 2

        request.request_count += 1
        assert request.request_count == 3


class TestRequestCoalescingServiceEdgeCases:
    """Test suite for RequestCoalescingService edge cases."""

    @pytest.mark.asyncio
    async def test_coalesce_with_special_characters_in_key(self):
        """Test that keys with special characters work correctly."""
        service = RequestCoalescingService()

        async def mock_fetch():
            return 'result'

        key_with_special = 'owner/repo/pull/123?param=value#fragment'
        result = await service.coalesce(key_with_special, mock_fetch)

        assert result == 'result'

    @pytest.mark.asyncio
    async def test_coalesce_empty_key(self):
        """Test that empty key works correctly."""
        service = RequestCoalescingService()

        async def mock_fetch():
            return 'result'

        result = await service.coalesce('', mock_fetch)

        assert result == 'result'

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(self):
        """Test multiple sequential requests to the same key."""
        service = RequestCoalescingService()

        fetch_count = []

        async def mock_fetch():
            fetch_count.append(1)
            await anyio.sleep(0.05)
            return f'result_{len(fetch_count)}'

        result1 = await service.coalesce('key1', mock_fetch)
        await anyio.sleep(0.1)
        result2 = await service.coalesce('key1', mock_fetch)

        # Should have called fetch twice (sequential requests don't coalesce)
        assert len(fetch_count) == 2
        assert result1 == 'result_1'
        assert result2 == 'result_2'
        assert len(service._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_cleanup_on_first_completion(self):
        """Test that pending request is cleaned after first completes."""
        service = RequestCoalescingService()

        async def mock_fetch():
            await anyio.sleep(0.05)
            return 'result'

        async with anyio.create_task_group() as tg:
            tg.start_soon(service.coalesce, 'key1', mock_fetch)
            tg.start_soon(service.coalesce, 'key1', mock_fetch)

        assert len(service._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_timeout(self):
        """Test concurrent requests with timeout on waiters."""
        service = RequestCoalescingService(max_waiters=5, logger=None)

        async def slow_fetch():
            await anyio.sleep(0.2)
            return 'result'

        timeout_occurred = False

        async def wait_for_first():
            nonlocal timeout_occurred
            try:
                return await service.coalesce('key1', slow_fetch, timeout=0.05)
            except TimeoutError:
                timeout_occurred = True

        async def wait_for_others():
            await anyio.sleep(0.01)
            try:
                return await service.coalesce('key1', slow_fetch, timeout=0.05)
            except TimeoutError:
                pass

        async with anyio.create_task_group() as tg:
            tg.start_soon(wait_for_first)
            tg.start_soon(wait_for_others)

        assert timeout_occurred
