"""Tests for GitLab strict PR diff session lifecycle."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from prdiffer.domain.config.gitlab_config import GitLabConfig
from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.pr_diff_cache import GITLAB_FULL_DIFF_CACHE_PREFIX
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason, PRDifferException
from prdiffer.infrastructure.vcs_providers.gitlab_diff_session import GitLabPRDiffSession, GitLabSessionPRDiffReader
from prdiffer.infrastructure.vcs_providers.gitlab_models import GitLabDiffSnapshot


def _snapshot(**kwargs: object) -> GitLabDiffSnapshot:
    state = str(kwargs.get("state", "empty"))
    base = str(kwargs.get("base_sha", "same"))
    head = str(kwargs.get("head_sha", "same" if state == "empty" else "head"))
    return GitLabDiffSnapshot(
        project_path=str(kwargs.get("project_path", "group/sub/project")),
        iid=int(kwargs.get("iid", 42)),
        version_id=int(kwargs.get("version_id", 7)),
        base_sha=base,
        start_sha=str(kwargs.get("start_sha", "start")),
        head_sha=head,
        state=state,
        real_size=int(kwargs["real_size"]) if "real_size" in kwargs else (0 if state == "empty" else 0),
        records=(),
    )

@pytest.mark.unit
@pytest.mark.anyio
class TestGitLabPRDiffSession:
    async def test_cache_identity_matches_snapshot(self) -> None:
        snap = _snapshot()
        session = GitLabPRDiffSession(
            snapshot=snap,
            operations=MagicMock(),
            content_fetcher=MagicMock(),
            assembler=MagicMock(),
            config=GitLabConfig(),
            runtime=MagicMock(),
            deadline_monotonic=1e18,
        )
        identity = session.cache_identity
        assert identity.cache_key.startswith(GITLAB_FULL_DIFF_CACHE_PREFIX)
        assert "group/sub" in identity.cache_key or "group/sub".casefold() in identity.cache_key
        assert identity.validation_token == "7:same:start:same"
        assert session.snapshot.head_sha == "same"
        await session.aclose()
        await session.aclose()  # idempotent

    async def test_build_once_and_close_blocks_second_build(self) -> None:
        snap = _snapshot(state="empty")
        content = MagicMock()
        content.fetch_all = AsyncMock(return_value=())
        assembler = MagicMock()
        assembler.assemble.return_value = PRDiff(files=())
        session = GitLabPRDiffSession(
            snapshot=snap,
            operations=MagicMock(),
            content_fetcher=content,
            assembler=assembler,
            config=GitLabConfig(),
            runtime=MagicMock(),
            deadline_monotonic=1e18,
        )
        result = await session.build_pr_diff()
        assert isinstance(result, PRDiff)
        with pytest.raises(PRDifferException):
            await session.build_pr_diff()
        await session.aclose()
        with pytest.raises(PRDifferException):
            await session.build_pr_diff()

    async def test_build_failure_still_allows_close(self) -> None:
        snap = _snapshot(state="collected", real_size=1)
        # force inventory fail via non-empty real_size with empty records
        snap = GitLabDiffSnapshot(
            project_path="g/p",
            iid=1,
            version_id=1,
            base_sha="b",
            start_sha="s",
            head_sha="h",
            state="collected",
            real_size=1,
            records=(),
        )
        session = GitLabPRDiffSession(
            snapshot=snap,
            operations=MagicMock(),
            content_fetcher=MagicMock(),
            assembler=MagicMock(),
            config=GitLabConfig(),
            runtime=MagicMock(),
            deadline_monotonic=1e18,
        )
        with pytest.raises(FullDiffIncompleteError) as exc:
            await session.build_pr_diff()
        assert exc.value.reason is FullDiffIncompleteReason.INVENTORY_TRUNCATED
        await session.aclose()
        assert session._closed is True


@pytest.mark.unit
@pytest.mark.anyio
class TestGitLabSessionReader:
    async def test_open_build_close_lifecycle(self) -> None:
        ops = MagicMock()
        ops.select_diff_snapshot.return_value = _snapshot(state="empty")
        content = MagicMock()
        content.fetch_all = AsyncMock(return_value=())
        assembler = MagicMock()
        assembler.assemble.return_value = PRDiff(
            files=(
                FileDiffResponse(
                    path="x.py",
                    status=EDIT_TYPE.ADDED,
                    stats=FileStats(additions=0, deletions=0),
                    diff="",
                ),
            )
        )
        reader = GitLabSessionPRDiffReader(
            operations=ops,
            runtime=MagicMock(),
            content_fetcher=content,
            assembler=assembler,
            config=GitLabConfig(),
        )
        result = await reader.get_pr_diff("group/sub", "project", 42)
        assert result is not None
        ops.select_diff_snapshot.assert_called_once_with("group/sub/project", 42)
        content.fetch_all.assert_awaited()
