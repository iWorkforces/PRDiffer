"""Tests for strict PRDiff cache identity and existing GitHub v2 helpers."""

from __future__ import annotations

import pytest

from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.pr_diff_cache import (
    GITHUB_FULL_DIFF_CACHE_PREFIX,
    PRDIFF_CACHE_SCHEMA_V2,
    StrictPRDiffCacheIdentity,
    github_full_diff_v2_identity,
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


def test_strict_identity_is_frozen() -> None:
    identity = StrictPRDiffCacheIdentity(
        cache_key="k",
        validation_token="t",
        schema_version=2,
    )
    with pytest.raises(Exception):
        identity.validation_token = "x"  # type: ignore[misc]
    with pytest.raises(Exception):
        identity.schema_version = 1  # type: ignore[misc]


def test_github_v2_identity_matches_existing_key_bytes() -> None:
    identity = github_full_diff_v2_identity("Owner", "Repo", 7, "abc")
    expected_key = github_full_diff_v2_key("Owner", "Repo", 7, "abc")
    assert identity.cache_key == expected_key
    assert identity.cache_key == f"{GITHUB_FULL_DIFF_CACHE_PREFIX}:owner:repo:7:abc"
    assert identity.validation_token == "abc"
    assert identity.schema_version == PRDIFF_CACHE_SCHEMA_V2


def test_github_v2_key_bytes_unchanged() -> None:
    """Regression: GitHub key format must remain byte-for-byte stable."""
    assert github_full_diff_v2_key("o", "r", 1, "h") == "github-full-diff-v2:o:r:1:h"


def test_unwrap_and_wrap_v2_unchanged() -> None:
    value = _diff()
    entry = wrap_pr_diff_for_cache(value)
    assert entry.schema_version == PRDIFF_CACHE_SCHEMA_V2
    assert unwrap_pr_diff_cache_value(entry) is value
    key = github_full_diff_v2_key("o", "r", 1, "h")
    assert unwrap_pr_diff_cache_value(value, key=key) is value
    assert unwrap_pr_diff_cache_value(value, key="legacy") is None
