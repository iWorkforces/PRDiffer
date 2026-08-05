"""Tests for GitLab inventory admission and record classification."""

from __future__ import annotations

import pytest

from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.infrastructure.vcs_providers.gitlab_inventory import admit_inventory, classify_diff_record
from prdiffer.infrastructure.vcs_providers.gitlab_models import GitLabDiffRecord, GitLabDiffSnapshot


def _snap(
    *,
    state: str = "collected",
    real_size: int | None = None,
    records: tuple[GitLabDiffRecord, ...] = (),
    base: str = "b",
    head: str = "h",
) -> GitLabDiffSnapshot:
    if real_size is None and state == "collected":
        real_size = len(records)
    return GitLabDiffSnapshot(
        project_path="g/p",
        iid=1,
        version_id=9,
        base_sha=base,
        start_sha="s",
        head_sha=head,
        state=state,
        real_size=real_size,
        records=records,
    )


def _rec(
    *,
    old_path: str = "a.py",
    new_path: str = "a.py",
    new_file: bool = False,
    deleted_file: bool = False,
    renamed_file: bool = False,
    a_mode: str | None = "100644",
    b_mode: str | None = "100644",
    diff: str | None = None,
    collapsed: bool = False,
    too_large: bool = False,
    generated_file: bool | None = None,
) -> GitLabDiffRecord:
    return GitLabDiffRecord(
        old_path=old_path,
        new_path=new_path,
        new_file=new_file,
        deleted_file=deleted_file,
        renamed_file=renamed_file,
        a_mode=a_mode,
        b_mode=b_mode,
        diff=diff,
        collapsed=collapsed,
        too_large=too_large,
        generated_file=generated_file,
    )


@pytest.mark.unit
class TestAdmitInventory:
    def test_collected_exact_size_success(self) -> None:
        records = (
            _rec(new_file=True, old_path="a.py", new_path="a.py"),
            _rec(deleted_file=True, old_path="b.py", new_path="b.py"),
            _rec(renamed_file=True, old_path="old.py", new_path="new.py"),
            _rec(old_path="m.py", new_path="m.py", a_mode="100644", b_mode="100755"),
            _rec(old_path="c.py", new_path="c.py", collapsed=True, diff=None),
            _rec(old_path="t.py", new_path="t.py", too_large=True, diff=None),
            _rec(old_path="g.py", new_path="g.py", generated_file=True),
        )
        admitted = admit_inventory(_snap(records=records), max_files_allowed=50)
        assert len(admitted) == 7
        assert [a.edit_type for a in admitted] == [
            EDIT_TYPE.ADDED,
            EDIT_TYPE.DELETED,
            EDIT_TYPE.RENAMED,
            EDIT_TYPE.MODIFIED,
            EDIT_TYPE.MODIFIED,
            EDIT_TYPE.MODIFIED,
            EDIT_TYPE.MODIFIED,
        ]
        assert [a.index for a in admitted] == list(range(7))

    def test_empty_equal_refs_success(self) -> None:
        admitted = admit_inventory(
            _snap(state="empty", real_size=0, records=(), base="same", head="same"),
            max_files_allowed=50,
        )
        assert admitted == ()

    def test_overflow_state_fails(self) -> None:
        with pytest.raises(FullDiffIncompleteError) as exc:
            admit_inventory(_snap(state="overflow", real_size=0, records=()), max_files_allowed=50)
        assert exc.value.reason is FullDiffIncompleteReason.INVENTORY_TRUNCATED

    def test_without_files_fails(self) -> None:
        with pytest.raises(FullDiffIncompleteError) as exc:
            admit_inventory(_snap(state="without_files", real_size=0, records=()), max_files_allowed=50)
        assert exc.value.reason is FullDiffIncompleteReason.INVENTORY_TRUNCATED

    def test_count_mismatch_fails(self) -> None:
        with pytest.raises(FullDiffIncompleteError) as exc:
            admit_inventory(_snap(records=(_rec(),), real_size=2), max_files_allowed=50)
        assert exc.value.reason is FullDiffIncompleteReason.INVENTORY_TRUNCATED

    def test_file_count_limit(self) -> None:
        records = tuple(_rec(old_path=f"{i}.py", new_path=f"{i}.py") for i in range(3))
        with pytest.raises(FullDiffIncompleteError) as exc:
            admit_inventory(_snap(records=records), max_files_allowed=2)
        assert exc.value.reason is FullDiffIncompleteReason.FILE_COUNT_LIMIT
        assert exc.value.details["observed"] == 3
        assert exc.value.details["limit"] == 2

    def test_conflicting_flags(self) -> None:
        with pytest.raises(FullDiffIncompleteError) as exc:
            classify_diff_record(_rec(new_file=True, deleted_file=True))
        assert exc.value.reason is FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS

    def test_rename_same_path_fails(self) -> None:
        with pytest.raises(FullDiffIncompleteError) as exc:
            classify_diff_record(_rec(renamed_file=True, old_path="a.py", new_path="a.py"))
        assert exc.value.reason is FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS

    def test_malformed_mode_fails(self) -> None:
        with pytest.raises(FullDiffIncompleteError) as exc:
            admit_inventory(_snap(records=(_rec(a_mode="644"),)), max_files_allowed=50)
        assert exc.value.reason is FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS
