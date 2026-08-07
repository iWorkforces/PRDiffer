"""Cross-request cancellation, capacity, and coalescing cleanup for strict diffs."""

from __future__ import annotations

import anyio
import pytest

from prdiffer.infrastructure.utils.coalescing_service import RequestCoalescingService


@pytest.mark.integration
@pytest.mark.anyio
async def test_coalesced_owner_cancel_allows_same_key_retry() -> None:
    service = RequestCoalescingService(max_waiters=10)
    started = anyio.Event()
    hold = anyio.Event()
    outcomes: dict[str, object] = {}

    async def blocked() -> str:
        started.set()
        await hold.wait()
        return "blocked"

    async def owner() -> None:
        try:
            await service.coalesce("k", blocked, timeout=30.0)
            outcomes["owner"] = "ok"
        except BaseException as exc:  # noqa: BLE001
            outcomes["owner"] = type(exc).__name__

    async with anyio.create_task_group() as tg:
        tg.start_soon(owner)
        await started.wait()
        tg.cancel_scope.cancel()

    stats = await service.get_stats()
    assert stats["pending_count"] == 0
    assert stats["total_waiters"] == 0

    fetch_count = 0

    async def ok() -> str:
        nonlocal fetch_count
        fetch_count += 1
        return "recovered"

    result = await service.coalesce("k", ok, timeout=5.0)
    assert result == "recovered"
    assert fetch_count == 1


@pytest.mark.integration
@pytest.mark.anyio
async def test_capacity_one_serializes_two_session_workers() -> None:
    """Two capacity-1 session opens cannot both hold the limiter simultaneously."""
    limiter = anyio.CapacityLimiter(1)
    in_flight = 0
    max_in_flight = 0
    first_hold = anyio.Event()
    second_started = anyio.Event()
    release_first = anyio.Event()

    async def first() -> None:
        nonlocal in_flight, max_in_flight
        async with limiter:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            first_hold.set()
            await release_first.wait()
            in_flight -= 1

    async def second() -> None:
        nonlocal in_flight, max_in_flight
        second_started.set()
        async with limiter:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            in_flight -= 1

    async with anyio.create_task_group() as tg:
        tg.start_soon(first)
        await first_hold.wait()
        tg.start_soon(second)
        await second_started.wait()
        # First still holds capacity; second is blocked on acquire.
        assert max_in_flight == 1
        assert in_flight == 1
        release_first.set()

    assert max_in_flight == 1
