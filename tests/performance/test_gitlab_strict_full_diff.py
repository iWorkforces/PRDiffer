"""Deterministic concurrency/deadline regressions for GitLab strict runtime."""

from __future__ import annotations

import threading
import time

import anyio
import pytest

from prdiffer.domain.config.gitlab_config import GitLabConfig
from prdiffer.domain.exceptions import TimeoutError as DomainTimeoutError
from prdiffer.infrastructure.vcs_providers.gitlab_runtime import GitLabRuntime


class CountingClient:
    active = 0
    max_active = 0
    closed = 0
    _lock = threading.Lock()

    def __init__(self, *args, **kwargs) -> None:
        self.session = type("S", (), {"close": lambda self: None})()

        class _Session:
            def close(self_inner) -> None:
                with CountingClient._lock:
                    CountingClient.active = max(0, CountingClient.active - 1)
                    CountingClient.closed += 1

        self.session = _Session()
        with CountingClient._lock:
            CountingClient.active += 1
            CountingClient.max_active = max(CountingClient.max_active, CountingClient.active)

    @classmethod
    def reset(cls) -> None:
        cls.active = 0
        cls.max_active = 0
        cls.closed = 0


@pytest.mark.slow
@pytest.mark.anyio
async def test_capacity_bounds_and_identical_ordering() -> None:
    CountingClient.reset()
    release = threading.Event()
    config = GitLabConfig(max_concurrent=4, timeout=30, pr_diff_request_timeout_seconds=180)
    runtime = GitLabRuntime(config, client_factory=CountingClient, limiter=anyio.CapacityLimiter(4))

    def work(_client: object) -> str:
        release.wait(timeout=2)
        return "ok"

    async def run_batch(n: int = 50) -> list[str]:
        results: list[str] = []

        async def one(i: int) -> None:
            results.append(await runtime.run_blocking(work))

        async with anyio.create_task_group() as tg:
            for i in range(n):
                tg.start_soon(one, i)
            await anyio.sleep(0.05)
            assert CountingClient.max_active <= 4
            release.set()
        return results

    out = await run_batch(50)
    assert len(out) == 50
    assert all(x == "ok" for x in out)
    assert CountingClient.max_active <= 4
    assert CountingClient.closed == 50


@pytest.mark.slow
@pytest.mark.anyio
async def test_owner_deadline_returns_e5004() -> None:
    CountingClient.reset()
    runtime = GitLabRuntime(
        GitLabConfig(timeout=30, pr_diff_request_timeout_seconds=180),
        client_factory=CountingClient,
        deadline_monotonic=time.monotonic() + 0.05,
    )

    def slow(_c: object) -> str:
        time.sleep(1)
        return "late"

    with pytest.raises(DomainTimeoutError) as exc:
        await runtime.run_blocking(slow)
    assert exc.value.error_code.code == "E5004"
