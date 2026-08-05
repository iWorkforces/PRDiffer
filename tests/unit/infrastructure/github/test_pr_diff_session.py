"""Tests for GitHub PR diff session isolation."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import anyio
import pytest

from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.pr_diff_cache import (
    PRDIFF_CACHE_SCHEMA_V2,
    github_full_diff_v2_key,
)
from prdiffer.domain.interfaces.pr_diff_reader import PRDiffSnapshot
from prdiffer.infrastructure.github.pr_diff_session import GitHubPRDiffSession


@pytest.mark.unit
def test_session_cache_identity_matches_github_v2_bytes() -> None:
    snapshot = PRDiffSnapshot("Owner", "Repo", 7, "baseSHA", "headSHA", 3)
    session = GitHubPRDiffSession(
        snapshot=snapshot,
        github_client=MagicMock(),
        repository=MagicMock(),
        pull_request=MagicMock(),
        service=MagicMock(),
        limiter=anyio.CapacityLimiter(1),
        deadline_monotonic=time.monotonic() + 30,
    )
    identity = session.cache_identity
    assert identity.cache_key == github_full_diff_v2_key("Owner", "Repo", 7, "headSHA")
    assert identity.cache_key == "github-full-diff-v2:owner:repo:7:headSHA"
    assert identity.validation_token == "headSHA"
    assert identity.schema_version == PRDIFF_CACHE_SCHEMA_V2


@pytest.mark.unit
@pytest.mark.anyio
async def test_session_build_uses_limiter_capacity_one() -> None:
    limiter = anyio.CapacityLimiter(1)
    service = MagicMock()
    service._generate_diff_content.return_value = []
    service._build_pr_diff_strict.return_value = PRDiff(files=())

    in_flight = 0
    max_in_flight = 0

    original_run = anyio.to_thread.run_sync

    async def tracking_run_sync(func, *args, **kwargs):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        try:
            return await original_run(func, *args, **kwargs)
        finally:
            in_flight -= 1

    session = GitHubPRDiffSession(
        snapshot=PRDiffSnapshot("o", "r", 1, "b", "h", 0),
        github_client=MagicMock(),
        repository=MagicMock(),
        pull_request=MagicMock(),
        service=service,
        limiter=limiter,
        deadline_monotonic=time.monotonic() + 30,
    )

    # Patch at module level used by session
    import prdiffer.infrastructure.github.pr_diff_session as mod

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(mod.anyio.to_thread, "run_sync", tracking_run_sync)
    try:
        result = await session.build_pr_diff()
        assert isinstance(result, PRDiff)
        assert max_in_flight == 1
    finally:
        monkeypatch.undo()
        await session.aclose()


@pytest.mark.unit
@pytest.mark.anyio
async def test_session_closes_idempotently() -> None:
    session = GitHubPRDiffSession(
        snapshot=PRDiffSnapshot("o", "r", 1, "b", "h", 0),
        github_client=MagicMock(),
        repository=MagicMock(),
        pull_request=MagicMock(),
        service=MagicMock(),
        limiter=anyio.CapacityLimiter(1),
        deadline_monotonic=time.monotonic() + 30,
    )
    await session.aclose()
    await session.aclose()
    assert session._closed is True
