"""Tests for GitHub full-diff v2 cache keys and value unwrapping."""

from __future__ import annotations

from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.pr_diff_cache import (
    GITHUB_FULL_DIFF_CACHE_PREFIX,
    PRDIFF_CACHE_SCHEMA_V2,
    PRDiffCacheEntryV2,
    github_full_diff_v2_key,
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


def test_github_v2_key_casefold() -> None:
    key = github_full_diff_v2_key("Owner", "Repo", 7, "abc")
    assert key == f"{GITHUB_FULL_DIFF_CACHE_PREFIX}:owner:repo:7:abc"


def test_unwrap_accepts_v2_entry() -> None:
    entry = wrap_pr_diff_for_cache(_diff())
    assert entry.schema_version == PRDIFF_CACHE_SCHEMA_V2
    assert unwrap_pr_diff_cache_value(entry) is entry.value


def test_unwrap_ignores_wrong_schema() -> None:
    bad = object()
    assert unwrap_pr_diff_cache_value(bad) is None


def test_unwrap_bare_prdiff_only_under_active_strict_keys() -> None:
    from prdiffer.domain.entities.pr_diff_cache import github_full_diff_v3_key

    value = _diff()
    assert unwrap_pr_diff_cache_value(value, key="owner/repo/pr/1") is None
    # Legacy v2 keys are ignored (no migration).
    assert unwrap_pr_diff_cache_value(value, key=github_full_diff_v2_key("o", "r", 1, "h")) is None
    mb = "b" * 40
    hd = "c" * 40
    assert unwrap_pr_diff_cache_value(value, key=github_full_diff_v3_key("o", "r", 1, mb, hd)) is value


def test_unwrap_rejects_wrong_version_entry() -> None:
    # Construct invalid entry via object.__new__ path would fail post_init;
    # ensure only schema 2 is valid at construction time.
    try:
        PRDiffCacheEntryV2(schema_version=1, value=_diff())
        assert False, "expected ValueError"
    except ValueError:
        pass
