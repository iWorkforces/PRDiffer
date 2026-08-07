"""Immutable GitHub tree/object descriptors and pure normalization helpers.

Infrastructure-only: never leak descriptors into domain DTOs. Public content
still normalizes to text + six-digit mode fields on ``FilePatchInfo``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from prdiffer.domain.entities.file_content import (
    FileContentAvailable,
    FileContentResult,
    FileContentUnavailable,
    FileContentUnavailableReason,
)
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason

_MODE_RE = re.compile(r"^[0-7]{6}$")
_OBJECT_ID_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")

MODE_REGULAR_FILE = "100644"
MODE_EXECUTABLE = "100755"
MODE_SYMLINK = "120000"
MODE_GITLINK = "160000"
MODE_TREE = "040000"

_REGULAR_BLOB_MODES = frozenset({MODE_REGULAR_FILE, MODE_EXECUTABLE})
_KNOWN_MODES = frozenset({MODE_REGULAR_FILE, MODE_EXECUTABLE, MODE_SYMLINK, MODE_GITLINK, MODE_TREE})


class GitObjectType(StrEnum):
    """Git object types relevant to PR content reconstruction."""

    BLOB = "blob"
    TREE = "tree"
    COMMIT = "commit"


@dataclass(frozen=True, slots=True)
class GitTreeEntry:
    """One path entry from an immutable recursive tree."""

    path: str
    mode: str
    object_type: GitObjectType
    object_id: str
    ref: str

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("tree entry path must be nonempty")
        if _MODE_RE.fullmatch(self.mode) is None:
            raise ValueError(f"invalid tree mode: {self.mode!r}")
        if _OBJECT_ID_RE.fullmatch(self.object_id.casefold()) is None:
            raise ValueError(f"invalid tree object id: {self.object_id!r}")
        object.__setattr__(self, "object_id", self.object_id.casefold())


@dataclass(frozen=True, slots=True)
class GitObjectText:
    """Normalized text payload for one tree-proven path at a ref."""

    path: str
    ref: str
    mode: str
    object_id: str
    text: str


@dataclass(frozen=True, slots=True)
class GitBuildContext:
    """Frozen build inputs for strict ordered file assembly."""

    repo_full_name: str
    merge_base_sha: str
    head_sha: str
    max_file_size_bytes: int


def require_git_mode(value: object, *, field: str = "mode") -> str:
    """Require a six-digit octal mode string."""
    if not isinstance(value, str) or _MODE_RE.fullmatch(value) is None:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message=f"Invalid git mode for {field}",
            observed=str(value),
        )
    return value


def require_object_id(value: object, *, field: str = "object_id") -> str:
    """Require a 40/64-char hexadecimal object id."""
    if not isinstance(value, str) or not value:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message=f"Missing git object id for {field}",
        )
    normalized = value.casefold()
    if _OBJECT_ID_RE.fullmatch(normalized) is None:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message=f"Invalid git object id for {field}",
            observed=value,
        )
    return normalized


def parse_git_object_type(value: object) -> GitObjectType:
    """Parse provider object type strings."""
    if not isinstance(value, str) or not value:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message="Missing git object type",
        )
    try:
        return GitObjectType(value.casefold())
    except ValueError as exc:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message=f"Unsupported git object type: {value}",
            observed=value,
        ) from exc


def synthesize_gitlink_text(object_id: str) -> str:
    """Canonical gitlink body used for full-context diffs (never traverses submodule)."""
    oid = require_object_id(object_id, field="gitlink")
    return f"Subproject commit {oid}\n"


def decode_regular_blob_bytes(
    data: bytes,
    *,
    path: str,
    ref: str,
    max_file_size_bytes: int,
    observed_size: int | None = None,
) -> FileContentResult:
    """Decode regular-file blob bytes into typed content (no cache side effects)."""
    size = observed_size if observed_size is not None else len(data)
    if size > max_file_size_bytes:
        return FileContentUnavailable(
            reason=FileContentUnavailableReason.FILE_SIZE_LIMIT,
            path=path,
            ref=ref,
            observed_size=size,
        )
    if b"\x00" in data:
        return FileContentUnavailable(
            reason=FileContentUnavailableReason.BINARY_CONTENT,
            path=path,
            ref=ref,
            observed_size=size,
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return FileContentUnavailable(
            reason=FileContentUnavailableReason.CONTENT_DECODE_FAILED,
            path=path,
            ref=ref,
            observed_size=size,
        )
    return FileContentAvailable(text=text)


def validate_tree_entry_consistency(entry: GitTreeEntry) -> None:
    """Reject mode/type combinations that cannot be reconstructed."""
    mode = entry.mode
    otype = entry.object_type
    if mode not in _KNOWN_MODES:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=entry.path,
            message=f"Unsupported tree mode {mode}",
            observed=mode,
        )
    if mode in _REGULAR_BLOB_MODES and otype is not GitObjectType.BLOB:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=entry.path,
            message="Regular file mode requires blob object type",
            observed=otype.value,
        )
    if mode == MODE_SYMLINK and otype is not GitObjectType.BLOB:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=entry.path,
            message="Symlink mode requires blob object type",
            observed=otype.value,
        )
    if mode == MODE_GITLINK and otype is not GitObjectType.COMMIT:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=entry.path,
            message="Gitlink mode requires commit object type",
            observed=otype.value,
        )
    if mode == MODE_TREE and otype is not GitObjectType.TREE:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=entry.path,
            message="Tree mode requires tree object type",
            observed=otype.value,
        )


def index_tree_entries(entries: list[GitTreeEntry]) -> dict[str, GitTreeEntry]:
    """Index entries by path; reject duplicate paths as ambiguous."""
    indexed: dict[str, GitTreeEntry] = {}
    for entry in entries:
        validate_tree_entry_consistency(entry)
        if entry.path in indexed:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
                path=entry.path,
                message="Ambiguous duplicate tree path",
            )
        indexed[entry.path] = entry
    return indexed


def require_tree_entry(
    tree: dict[str, GitTreeEntry],
    path: str,
    *,
    ref: str,
) -> GitTreeEntry:
    """Require a selected path exists as a non-directory leaf in the tree."""
    entry = tree.get(path)
    if entry is None:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
            path=path,
            message=f"Selected path missing from tree at {ref}",
        )
    if entry.mode == MODE_TREE or entry.object_type is GitObjectType.TREE:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
            path=path,
            message="Selected path is a directory tree entry",
        )
    return entry


def require_distinct_rename_previous(previous_filename: object, path: str) -> str:
    """Reject renames lacking a distinct previous path (before any content fetch)."""
    if not isinstance(previous_filename, str) or not previous_filename:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=path,
            message="Rename lacks previous_filename",
        )
    if previous_filename == path:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=path,
            previous_path=previous_filename,
            message="Rename previous_filename must differ from path",
        )
    return previous_filename
