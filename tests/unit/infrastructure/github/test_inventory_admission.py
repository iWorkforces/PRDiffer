"""Tests for authoritative inventory validation and selected-file admission."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.infrastructure.github.inventory import (
    MAX_AUTHORITATIVE_CHANGED_FILES,
    prepare_selected_inventory,
    select_files_with_admission,
    validate_authoritative_inventory,
)


def _files(n: int, *, prefix: str = "f"):
    return [SimpleNamespace(filename=f"{prefix}{i}.py") for i in range(n)]


@pytest.mark.unit
class TestValidateAuthoritativeInventory:
    def test_happy_exact_3000(self) -> None:
        validate_authoritative_inventory(authoritative_changed_files=3000, enumerated_count=3000)

    def test_happy_zero(self) -> None:
        validate_authoritative_inventory(authoritative_changed_files=0, enumerated_count=0)

    def test_authoritative_3001_rejected(self) -> None:
        with pytest.raises(FullDiffIncompleteError) as exc:
            validate_authoritative_inventory(authoritative_changed_files=3001, enumerated_count=3000)
        assert exc.value.reason is FullDiffIncompleteReason.INVENTORY_TRUNCATED
        assert exc.value.details["observed"] == 3001
        assert exc.value.details["limit"] == MAX_AUTHORITATIVE_CHANGED_FILES

    def test_mismatch_250_249_rejected(self) -> None:
        with pytest.raises(FullDiffIncompleteError) as exc:
            validate_authoritative_inventory(authoritative_changed_files=250, enumerated_count=249)
        assert exc.value.reason is FullDiffIncompleteReason.INVENTORY_TRUNCATED
        assert exc.value.details["observed"] == 249
        assert exc.value.details["limit"] == 250


@pytest.mark.unit
class TestSelectedAdmission:
    def test_selected_n_succeeds(self) -> None:
        files = _files(5)
        selected = select_files_with_admission(files, is_valid_file=lambda _: True, max_files_allowed=5)
        assert len(selected) == 5

    def test_selected_n_plus_one_fails(self) -> None:
        files = _files(6)
        with pytest.raises(FullDiffIncompleteError) as exc:
            select_files_with_admission(files, is_valid_file=lambda _: True, max_files_allowed=5)
        assert exc.value.reason is FullDiffIncompleteReason.FILE_COUNT_LIMIT
        assert exc.value.details["observed"] == 6
        assert exc.value.details["limit"] == 5

    def test_filtering_before_admission(self) -> None:
        files = _files(10)
        selected = select_files_with_admission(
            files,
            is_valid_file=lambda name: name.endswith("0.py") or name.endswith("1.py"),
            max_files_allowed=3,
        )
        assert len(selected) == 2


@pytest.mark.unit
class TestPrepareSelectedInventory:
    def test_two_pages_order_preserved(self) -> None:
        page1 = _files(2, prefix="a")
        page2 = _files(2, prefix="b")
        pages = page1 + page2
        selected = prepare_selected_inventory(
            authoritative_changed_files=4,
            provider_files=pages,
            is_valid_file=lambda _: True,
            max_files_allowed=50,
        )
        assert [f.filename for f in selected] == ["a0.py", "a1.py", "b0.py", "b1.py"]

    def test_zero_file_pr_valid(self) -> None:
        selected = prepare_selected_inventory(
            authoritative_changed_files=0,
            provider_files=[],
            is_valid_file=lambda _: True,
            max_files_allowed=50,
        )
        assert selected == []
