"""Tests for PRDiff cache *value* schema (PRDiffCacheEntryV2) and unwrap."""

from __future__ import annotations

from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.pr_diff_cache import (
    GITHUB_FULL_DIFF_CACHE_PREFIX_V3,
    PRDIFF_CACHE_SCHEMA_V2,
    PRDiffCacheEntryV2,
    github_full_diff_v3_key,
    unwrap_pr_diff_cache_value,
    wrap_pr_diff_for_cache,
)


def _diff() -> PRDiff:
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


def test_unwrap_accepts_value_schema_entry() -> None:
    entry = wrap_pr_diff_for_cache(_diff())
    assert entry.schema_version == PRDIFF_CACHE_SCHEMA_V2
    assert unwrap_pr_diff_cache_value(entry) is entry.value


def test_unwrap_ignores_wrong_type() -> None:
    assert unwrap_pr_diff_cache_value(object()) is None


def test_unwrap_bare_prdiff_only_under_strict_github_or_gitlab_keys() -> None:
    value = _diff()
    assert unwrap_pr_diff_cache_value(value, key="owner/repo/pr/1") is None
    assert unwrap_pr_diff_cache_value(value, key="not-a-strict-key:o:r:1:h") is None
    mb = "b" * 40
    hd = "c" * 40
    key = github_full_diff_v3_key("o", "r", 1, mb, hd)
    assert key.startswith(GITHUB_FULL_DIFF_CACHE_PREFIX_V3)
    assert unwrap_pr_diff_cache_value(value, key=key) is value


def test_unwrap_rejects_wrong_value_schema_version() -> None:
    try:
        PRDiffCacheEntryV2(schema_version=1, value=_diff())
        assert False, "expected ValueError"
    except ValueError:
        pass
