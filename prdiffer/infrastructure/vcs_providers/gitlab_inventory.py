"""GitLab inventory admission and file-state classification."""

from __future__ import annotations

import re
from dataclasses import dataclass

from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.infrastructure.vcs_providers.gitlab_models import GitLabDiffRecord, GitLabDiffSnapshot

_GIT_MODE_RE = re.compile(r"^[0-7]{6}$")


@dataclass(frozen=True, slots=True)
class GitLabInventoryFile:
    """Admitted inventory entry with classified edit type."""

    record: GitLabDiffRecord
    edit_type: EDIT_TYPE
    index: int


def _require_git_mode(value: str | None, *, path: str, field: str) -> None:
    if value is None:
        return
    if not _GIT_MODE_RE.fullmatch(value):
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message=f"Malformed required Git mode in {field}",
            path=path,
        )


def classify_diff_record(record: GitLabDiffRecord) -> EDIT_TYPE:
    """Classify exactly one of added/deleted/renamed/modified; fail on conflicts."""
    flags = (record.new_file, record.deleted_file, record.renamed_file)
    if sum(1 for f in flags if f) > 1:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message="Conflicting GitLab change flags",
            path=record.new_path or record.old_path,
        )
    if record.new_file:
        if not record.new_path:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
                message="Added file missing new_path",
            )
        return EDIT_TYPE.ADDED
    if record.deleted_file:
        if not record.old_path:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
                message="Deleted file missing old_path",
            )
        return EDIT_TYPE.DELETED
    if record.renamed_file:
        if not record.old_path or not record.new_path:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
                message="Renamed file missing required paths",
                path=record.new_path or record.old_path,
            )
        if record.old_path == record.new_path:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
                message="Rename requires distinct old_path and new_path",
                path=record.new_path,
                previous_path=record.old_path,
            )
        return EDIT_TYPE.RENAMED
    # modified / mode-only
    if not record.new_path and not record.old_path:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message="Modified file missing paths",
        )
    return EDIT_TYPE.MODIFIED


def admit_inventory(
    snapshot: GitLabDiffSnapshot,
    *,
    max_files_allowed: int,
) -> tuple[GitLabInventoryFile, ...]:
    """Validate version state/cardinality and classify ordered records.

    Fail closed before any content retrieval.
    """
    state = (snapshot.state or "").strip().lower()
    n = len(snapshot.records)
    equal_refs = snapshot.base_sha == snapshot.head_sha

    if state == "empty":
        if not equal_refs or n != 0:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.INVENTORY_TRUNCATED,
                message="Ambiguous empty inventory state",
                observed=n,
            )
        if snapshot.real_size not in (None, 0):
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.INVENTORY_TRUNCATED,
                message="Empty inventory real_size must be absent or zero",
                observed=snapshot.real_size,
                limit=0,
            )
        return ()

    if state != "collected":
        # overflow, without_files, timeout, unknown, missing
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message=f"MR diff version state is not collected (state={state!r})",
            observed=n,
        )

    if snapshot.real_size is None:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message="collected inventory requires decimal real_size",
            observed=n,
        )
    if snapshot.real_size != n:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message="real_size does not match embedded diffs length",
            observed=n,
            limit=snapshot.real_size,
        )

    if n > max_files_allowed:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.FILE_COUNT_LIMIT,
            message=f"File count {n} exceeds max_files_allowed {max_files_allowed}",
            observed=n,
            limit=max_files_allowed,
        )

    admitted: list[GitLabInventoryFile] = []
    for index, record in enumerate(snapshot.records):
        edit_type = classify_diff_record(record)
        path = record.new_path or record.old_path
        _require_git_mode(record.a_mode, path=path, field="a_mode")
        _require_git_mode(record.b_mode, path=path, field="b_mode")
        admitted.append(GitLabInventoryFile(record, edit_type, index))
    return tuple(admitted)
