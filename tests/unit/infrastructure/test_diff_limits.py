"""Strict full-diff size limit tests (no truncation success path)."""

import pytest

from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.infrastructure.utils.diff_limits import (
    apply_diff_limits,
    assert_aggregate_within_limit,
    assert_diff_within_limit,
)


def test_per_file_exact_boundary_succeeds() -> None:
    content = "a" * 10
    assert_diff_within_limit(content, 10)
    result, metadata = apply_diff_limits(content, max_chars=10, truncation_notice="[TRUNC]")
    assert result == content
    assert metadata == {}


def test_per_file_plus_one_raises() -> None:
    content = "a" * 11
    with pytest.raises(FullDiffIncompleteError) as exc:
        assert_diff_within_limit(content, 10, path="x.py")
    assert exc.value.reason is FullDiffIncompleteReason.RESPONSE_SIZE_LIMIT
    assert exc.value.details["observed"] == 11
    assert exc.value.details["limit"] == 10
    assert exc.value.details["path"] == "x.py"


def test_apply_diff_limits_no_truncation_notice() -> None:
    content = "a" * 50
    with pytest.raises(FullDiffIncompleteError):
        apply_diff_limits(content, max_chars=10, truncation_notice="[TRUNC]")


def test_aggregate_exact_boundary_succeeds() -> None:
    diffs = ["a" * 40, "b" * 60]
    total = assert_aggregate_within_limit(diffs, 100)
    assert total == 100


def test_aggregate_plus_one_raises() -> None:
    diffs = ["a" * 40, "b" * 61]
    with pytest.raises(FullDiffIncompleteError) as exc:
        assert_aggregate_within_limit(diffs, 100)
    assert exc.value.reason is FullDiffIncompleteReason.RESPONSE_SIZE_LIMIT
    assert exc.value.details["observed"] == 101
    assert exc.value.details["limit"] == 100


def test_apply_diff_limits_noop_when_under_limit() -> None:
    content = "short"
    result, metadata = apply_diff_limits(content, max_chars=100, truncation_notice="[TRUNC]")
    assert result == content
    assert metadata == {}
