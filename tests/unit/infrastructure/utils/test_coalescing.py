"""Tests for RequestCoalescingService request deduplication."""

import pytest
import anyio
from unittest.mock import Mock, AsyncMock, patch

from prdiffer.infrastructure.utils.coalescing_service import (
    RequestCoalescingService,
    CoalescedRequest,
    get_request_coalescing_service,
    DEFAULT_MAX_WAITERS,
)


@pytest.fixture
def coalescing_service():
    """Create RequestCoalescingService with mocked dependencies."""
    mock_logger = Mock()
    with patch("prdiffer.infrastructure.utils.coalescing_service.get_settings_service") as mock_settings:
        mock_settings.return_value.get.return_value = 100
        service = RequestCoalescingService(logger=mock_logger, max_waiters=50)
    return service


@pytest.mark.unit
class TestCoalescedRequest:
    """Tests for CoalescedRequest dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        req = CoalescedRequest(key="test_key")
        assert req.key == "test_key"
        assert req.result is None
        assert req.exception is None
        assert req.request_count == 1
        assert isinstance(req.event, anyio.Event)

    def test_custom_values(self):
        """Custom values are stored."""
        req = CoalescedRequest(key="k", request_count=5)
        assert req.request_count == 5


@pytest.mark.unit
class TestRequestCoalescingServiceInit:
    """Tests for service initialization."""

    def test_init_with_logger(self):
        """Logger is stored."""
        mock_logger = Mock()
        with patch("prdiffer.infrastructure.utils.coalescing_service.get_settings_service") as mock_settings:
            mock_settings.return_value.get.return_value = DEFAULT_MAX_WAITERS
            service = RequestCoalescingService(logger=mock_logger, max_waiters=50)
        assert service._logger is mock_logger

    def test_init_max_waiters_from_param(self):
        """max_waiters from parameter is used."""
        with patch("prdiffer.infrastructure.utils.coalescing_service.get_settings_service") as mock_settings:
            mock_settings.return_value.get.return_value = DEFAULT_MAX_WAITERS
            service = RequestCoalescingService(logger=Mock(), max_waiters=25)
        assert service._max_waiters == 25


@pytest.mark.unit
class TestCoalesceBasic:
    """Tests for basic coalesce functionality."""

    @pytest.mark.anyio
    async def test_single_request_executes(self, coalescing_service):
        """Single request executes fetch_func and returns result."""
        fetch_func = AsyncMock(return_value="result_data")

        result = await coalescing_service.coalesce("key1", fetch_func)

        assert result == "result_data"
        fetch_func.assert_called_once()

    @pytest.mark.anyio
    async def test_different_keys_execute_separately(self, coalescing_service):
        """Different keys execute separate fetch functions."""
        fetch1 = AsyncMock(return_value="data1")
        fetch2 = AsyncMock(return_value="data2")

        result1 = await coalescing_service.coalesce("key1", fetch1)
        result2 = await coalescing_service.coalesce("key2", fetch2)

        assert result1 == "data1"
        assert result2 == "data2"
        fetch1.assert_called_once()
        fetch2.assert_called_once()

    @pytest.mark.anyio
    async def test_fetch_exception_propagates(self, coalescing_service):
        """Exception from fetch_func propagates to caller."""
        fetch_func = AsyncMock(side_effect=ValueError("fetch failed"))

        with pytest.raises(ValueError, match="fetch failed"):
            await coalescing_service.coalesce("key1", fetch_func)

    @pytest.mark.anyio
    async def test_timeout_raises(self, coalescing_service):
        """Timeout raises TimeoutError."""

        async def slow_func():
            await anyio.sleep(5)
            return "late"

        with pytest.raises(TimeoutError):
            await coalescing_service.coalesce("key1", slow_func, timeout=0.1)


@pytest.mark.unit
class TestCoalesceDeduplication:
    """Tests for request deduplication behavior."""

    @pytest.mark.anyio
    async def test_concurrent_requests_deduplicated(self, coalescing_service):
        """Concurrent requests for same key share one fetch."""
        call_count = 0

        async def counting_fetch():
            nonlocal call_count
            call_count += 1
            await anyio.sleep(0.1)
            return "shared_result"

        results = []

        async def make_request():
            result = await coalescing_service.coalesce("same_key", counting_fetch)
            results.append(result)

        async with anyio.create_task_group() as tg:
            for _ in range(5):
                tg.start_soon(make_request)

        # All should get the same result
        assert all(r == "shared_result" for r in results)
        # Fetch should have been called only once (or at most twice due to race)
        assert call_count <= 2

    @pytest.mark.anyio
    async def test_sequential_requests_execute_separately(self, coalescing_service):
        """Sequential requests for same key execute separately."""
        call_count = 0

        async def counting_fetch():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        result1 = await coalescing_service.coalesce("key1", counting_fetch)
        result2 = await coalescing_service.coalesce("key1", counting_fetch)

        assert result1 == "result_1"
        assert result2 == "result_2"
        assert call_count == 2


@pytest.mark.unit
class TestGetStats:
    """Tests for get_stats method."""

    @pytest.mark.anyio
    async def test_stats_empty(self, coalescing_service):
        """Empty service reports zero stats."""
        stats = await coalescing_service.get_stats()
        assert stats["pending_count"] == 0
        assert stats["pending_keys"] == []
        assert stats["total_waiters"] == 0

    @pytest.mark.anyio
    async def test_stats_after_completed_request(self, coalescing_service):
        """Stats are clean after completed request."""
        await coalescing_service.coalesce("key1", AsyncMock(return_value="data"))
        stats = await coalescing_service.get_stats()
        assert stats["pending_count"] == 0


@pytest.mark.unit
class TestClear:
    """Tests for clear method."""

    @pytest.mark.anyio
    async def test_clear_removes_pending(self, coalescing_service):
        """Clear removes all pending requests."""
        await coalescing_service.clear()
        stats = await coalescing_service.get_stats()
        assert stats["pending_count"] == 0


@pytest.mark.unit
class TestGetRequestCoalescingServiceSingleton:
    """Tests for singleton factory function."""

    def test_singleton_returns_instance(self):
        """get_request_coalescing_service returns an instance."""
        with patch(
            "prdiffer.infrastructure.utils.coalescing_service._request_coalescing_service",
            None,
        ):
            service = get_request_coalescing_service()
            assert isinstance(service, RequestCoalescingService)


@pytest.mark.unit
class TestCoalescingCancellationCleanup:
    """Owner cancellation must wake waiters and clear pending state."""

    @pytest.mark.anyio
    async def test_owner_cancel_wakes_waiter_and_clears_pending(self, coalescing_service):
        owner_started = anyio.Event()
        release_owner = anyio.Event()
        outcomes: dict[str, object] = {}

        async def slow_fetch():
            owner_started.set()
            await release_owner.wait()
            return "should-not-return"

        async def owner():
            try:
                await coalescing_service.coalesce("same", slow_fetch, timeout=30.0)
                outcomes["owner"] = "ok"
            except BaseException as exc:  # noqa: BLE001 — assert cancel identity
                outcomes["owner"] = type(exc)

        async def waiter():
            await owner_started.wait()

            async def should_not_run():
                raise AssertionError("waiter must not start a second fetch")

            try:
                await coalescing_service.coalesce("same", should_not_run, timeout=30.0)
                outcomes["waiter"] = "ok"
            except BaseException as exc:  # noqa: BLE001
                outcomes["waiter"] = type(exc)

        async with anyio.create_task_group() as tg:
            tg.start_soon(owner)
            tg.start_soon(waiter)
            await owner_started.wait()
            # Cancel the whole group → owner cancelled mid-fetch; waiter must terminate.
            tg.cancel_scope.cancel()

        stats = await coalescing_service.get_stats()
        assert stats["pending_count"] == 0
        assert stats["total_waiters"] == 0
        assert stats["pending_keys"] == []
        # Both sides terminated (cancel), not timed out hanging.
        assert outcomes.get("owner") is not None
        assert outcomes.get("waiter") is not None

    @pytest.mark.anyio
    async def test_same_key_works_after_cancelled_owner(self, coalescing_service):
        owner_started = anyio.Event()
        hold = anyio.Event()

        async def blocked_fetch():
            owner_started.set()
            await hold.wait()
            return "blocked"

        async with anyio.create_task_group() as tg:
            tg.start_soon(coalescing_service.coalesce, "k", blocked_fetch)
            await owner_started.wait()
            tg.cancel_scope.cancel()

        stats = await coalescing_service.get_stats()
        assert stats["pending_count"] == 0

        fetch = AsyncMock(return_value="recovered")
        result = await coalescing_service.coalesce("k", fetch, timeout=5.0)
        assert result == "recovered"
        fetch.assert_awaited_once()


@pytest.mark.unit
class TestCoalescingImportIdentity:
    def test_package_and_flat_class_and_singleton_are_identical(self):
        from prdiffer.infrastructure.utils import coalescing_service as flat
        from prdiffer.infrastructure.utils.coalescing import service as pkg
        from prdiffer.infrastructure.utils import coalescing as pkg_init

        assert flat.RequestCoalescingService is pkg.RequestCoalescingService
        assert flat.RequestCoalescingService is pkg_init.RequestCoalescingService
        assert flat.get_request_coalescing_service is pkg.get_request_coalescing_service
        # Reset then compare singleton identity across import paths
        flat._request_coalescing_service = None
        a = flat.get_request_coalescing_service()
        b = pkg.get_request_coalescing_service()
        c = pkg_init.get_request_coalescing_service()
        assert a is b is c
