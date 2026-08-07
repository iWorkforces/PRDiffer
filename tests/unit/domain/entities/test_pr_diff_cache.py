"""Tests for strict PRDiff cache identity (GitHub v3 + GitLab v1)."""

from __future__ import annotations

import pytest

from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.pr_diff_cache import (
    GITHUB_FULL_DIFF_CACHE_PREFIX_V3,
    PRDIFF_CACHE_SCHEMA_V2,
    StrictPRDiffCacheIdentity,
    github_full_diff_v3_identity,
    github_full_diff_v3_key,
    unwrap_pr_diff_cache_value,
    wrap_pr_diff_for_cache,
)

MB = "b" * 40
HD = "c" * 40
MB2 = "e" * 40


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


def test_github_v3_identity_includes_merge_base_and_head() -> None:
    identity = github_full_diff_v3_identity("Owner", "Repo", 7, MB, HD)
    expected_key = github_full_diff_v3_key("Owner", "Repo", 7, MB, HD)
    assert identity.cache_key == expected_key
    assert identity.cache_key == f"{GITHUB_FULL_DIFF_CACHE_PREFIX_V3}:owner:repo:7:{MB}:{HD}"
    assert identity.validation_token == f"{MB}:{HD}"
    assert identity.schema_version == PRDIFF_CACHE_SCHEMA_V2


def test_github_v3_distinct_merge_base_same_head() -> None:
    a = github_full_diff_v3_identity("o", "r", 1, MB, HD)
    b = github_full_diff_v3_identity("o", "r", 1, MB2, HD)
    assert a.cache_key != b.cache_key
    assert a.validation_token != b.validation_token


def test_unwrap_and_wrap_value_schema_under_v3_key() -> None:
    value = _diff()
    entry = wrap_pr_diff_for_cache(value)
    assert entry.schema_version == PRDIFF_CACHE_SCHEMA_V2
    assert unwrap_pr_diff_cache_value(entry) is value
    key = github_full_diff_v3_key("o", "r", 1, MB, HD)
    identity = github_full_diff_v3_identity("o", "r", 1, MB, HD)
    assert unwrap_pr_diff_cache_value(value, key=key) is value
    assert unwrap_pr_diff_cache_value(value, key=key, identity=identity) is value
    assert unwrap_pr_diff_cache_value(entry, key=key, identity=identity) is value
    assert unwrap_pr_diff_cache_value(value, key="legacy") is None
    assert unwrap_pr_diff_cache_value(value, key="not-a-strict-key:o:r:1:h") is None
