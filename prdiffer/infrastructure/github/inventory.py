"""Authoritative PR file inventory validation and selected-file admission.

Strict completeness applies after configured ignore/extension selection.
Provider inventory must be proven complete before selection.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol, cast, Any

from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason

# GitHub REST list-pull-request-files supports full pagination through 3000 files.
MAX_AUTHORITATIVE_CHANGED_FILES = 3000


class _NamedFile(Protocol):
    filename: str


def materialize_pr_files(files: Iterable[object]) -> list[object]:
    """Fully enumerate provider file pages in source order."""
    return list(files)


def validate_authoritative_inventory(
    *,
    authoritative_changed_files: int,
    enumerated_count: int,
) -> None:
    """Reject truncated/mismatched inventories before any content loading.

    Rules:
    - Authoritative counts over 3000 fail with INVENTORY_TRUNCATED (before content).
    - Enumerated count must equal authoritative count (including both zero).
    """
    if authoritative_changed_files < 0 or enumerated_count < 0:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message="Negative inventory counts are invalid",
            observed=enumerated_count,
            limit=authoritative_changed_files,
        )

    if authoritative_changed_files > MAX_AUTHORITATIVE_CHANGED_FILES:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message=(
                f"Authoritative changed-file count {authoritative_changed_files} exceeds "
                f"GitHub pagination ceiling {MAX_AUTHORITATIVE_CHANGED_FILES}"
            ),
            observed=authoritative_changed_files,
            limit=MAX_AUTHORITATIVE_CHANGED_FILES,
        )

    if enumerated_count != authoritative_changed_files:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message=(
                f"Enumerated file count {enumerated_count} does not match "
                f"authoritative changed_files {authoritative_changed_files}"
            ),
            observed=enumerated_count,
            limit=authoritative_changed_files,
        )


def select_files_with_admission(
    files: Sequence[_NamedFile],
    *,
    is_valid_file,
    max_files_allowed: int,
) -> list[_NamedFile]:
    """Apply ignore/extension policy then enforce selected-file admission limit.

    Exactly N selected files succeeds; N+1 raises FILE_COUNT_LIMIT before content.
    """
    if not isinstance(max_files_allowed, int) or isinstance(max_files_allowed, bool) or max_files_allowed <= 0:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.FILE_COUNT_LIMIT,
            message="max_files_allowed must be a positive integer",
            observed=0,
            limit=max_files_allowed if isinstance(max_files_allowed, int) else 0,
        )

    selected: list[_NamedFile] = [f for f in files if is_valid_file(f.filename)]
    if len(selected) > max_files_allowed:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.FILE_COUNT_LIMIT,
            message=(
                f"Selected file count {len(selected)} exceeds admission limit {max_files_allowed}"
            ),
            observed=len(selected),
            limit=max_files_allowed,
        )
    return selected


def resolve_authoritative_count(pull_request: object, enumerated_count: int) -> int:
    """Read PR.changed_files when it is a real int; otherwise trust enumeration."""
    raw = getattr(pull_request, "changed_files", None)
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw
    return enumerated_count


def prepare_selected_inventory(
    *,
    authoritative_changed_files: int | None,
    provider_files: Iterable[object],
    is_valid_file,
    max_files_allowed: int,
    pull_request: object | None = None,
) -> list[object]:
    """Materialize, validate inventory, then select with hard admission limit."""
    enumerated = materialize_pr_files(provider_files)
    if authoritative_changed_files is None and pull_request is not None:
        authoritative = resolve_authoritative_count(pull_request, len(enumerated))
    elif authoritative_changed_files is None:
        authoritative = len(enumerated)
    else:
        authoritative = authoritative_changed_files
    validate_authoritative_inventory(
        authoritative_changed_files=authoritative,
        enumerated_count=len(enumerated),
    )
    limit = max_files_allowed if isinstance(max_files_allowed, int) and not isinstance(max_files_allowed, bool) else 50
    selected = select_files_with_admission(
        cast(Sequence[_NamedFile], enumerated),
        is_valid_file=is_valid_file,
        max_files_allowed=limit,
    )
    return cast(list[object], selected)
