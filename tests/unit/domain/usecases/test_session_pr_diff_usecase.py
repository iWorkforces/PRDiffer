"""Tests for session-capable vs legacy PRDiff reader dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.interfaces.pr_diff_reader import PRDiffSnapshot
from prdiffer.domain.usecases.pr_diff_usecases import GetPRDiffUseCase


def _pr_diff() -> PRDiff:
    return PRDiff(
        files=(
            FileDiffResponse(
                path="a.py",
                status=EDIT_TYPE.MODIFIED,
                stats=FileStats(additions=1, deletions=0),
                diff="+x",
            ),
        )
    )


@dataclass
class FakeSession:
    snapshot: PRDiffSnapshot
    build: AsyncMock
    closed: bool = False

    async def build_pr_diff(self) -> PRDiff:
        return await self.build()

    async def aclose(self) -> None:
        self.closed = True


class SessionReader:
    def __init__(self, session: FakeSession):
        self.session = session
        self.open_calls = 0
        self.get_pr_diff = AsyncMock(side_effect=AssertionError("legacy get_pr_diff must not be used"))
        self.get_latest_commit_sha = AsyncMock(side_effect=AssertionError("legacy sha must not be used"))

    async def open_pr_diff_session(self, owner: str, repo: str, pr: int, /) -> FakeSession:
        self.open_calls += 1
        return self.session


class LegacyReader:
    def __init__(self):
        self.get_latest_commit_sha = AsyncMock(return_value="sha1")
        self.get_pr_diff = AsyncMock(return_value=_pr_diff())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_path_uses_snapshot_and_closes() -> None:
    cache = MagicMock()
    cache.get_cache_key.return_value = "key"
    cache.get_optimistic = AsyncMock(return_value=(None, None))
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()

    build = AsyncMock(return_value=_pr_diff())
    session = FakeSession(
        snapshot=PRDiffSnapshot("o", "r", 1, "base", "head", 1),
        build=build,
    )
    reader = SessionReader(session)
    use_case = GetPRDiffUseCase(reader, cache, cache_hit_optimization_enabled=False)

    result = await use_case.execute("o", "r", 1)

    assert result is not None
    assert reader.open_calls == 1
    build.assert_awaited_once()
    cache.set.assert_awaited_once()
    assert cache.set.await_args.args[1] == "head"
    assert session.closed is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_cache_hit_closes_without_build() -> None:
    cached = _pr_diff()
    cache = MagicMock()
    cache.get_cache_key.return_value = "key"
    cache.get_optimistic = AsyncMock(return_value=(None, None))
    cache.get = AsyncMock(return_value=cached)
    cache.set = AsyncMock()

    build = AsyncMock()
    session = FakeSession(
        snapshot=PRDiffSnapshot("o", "r", 1, "base", "head", 1),
        build=build,
    )
    reader = SessionReader(session)
    use_case = GetPRDiffUseCase(reader, cache)

    result = await use_case.execute("o", "r", 1)

    assert result is cached
    build.assert_not_called()
    cache.set.assert_not_called()
    assert session.closed is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_legacy_gitlab_path_unchanged() -> None:
    cache = MagicMock()
    cache.get_cache_key.return_value = "key"
    cache.get_optimistic = AsyncMock(return_value=(None, None))
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()

    reader = LegacyReader()
    use_case = GetPRDiffUseCase(reader, cache)

    result = await use_case.execute("o", "r", 1)

    assert result is not None
    reader.get_latest_commit_sha.assert_awaited()
    reader.get_pr_diff.assert_awaited_once()
    cache.set.assert_awaited_once()
