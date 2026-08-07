"""Immutable GitLab repository tree/object helpers for strict full-diff.

Infrastructure-only descriptors. Regular files may still use ``files.raw`` when
tree-proven; symlink (120000) and gitlink (160000) never call raw-file APIs.
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
_LEAF_MODES = frozenset({MODE_REGULAR_FILE, MODE_EXECUTABLE, MODE_SYMLINK, MODE_GITLINK})


class GitLabObjectType(StrEnum):
    BLOB = "blob"
    TREE = "tree"
    COMMIT = "commit"


@dataclass(frozen=True, slots=True)
class GitLabTreeEntry:
    """One recursive repository-tree leaf at an immutable ref."""

    path: str
    mode: str
    object_type: GitLabObjectType
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


def require_object_id(value: object, *, field: str = "object_id") -> str:
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


def require_git_mode(value: object, *, field: str = "mode") -> str:
    if not isinstance(value, str) or _MODE_RE.fullmatch(value) is None:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message=f"Invalid git mode for {field}",
            observed=str(value),
        )
    return value


def parse_object_type(value: object) -> GitLabObjectType:
    if not isinstance(value, str) or not value:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message="Missing git object type",
        )
    try:
        return GitLabObjectType(value.casefold())
    except ValueError as exc:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message=f"Unsupported git object type: {value}",
            observed=value,
        ) from exc


def synthesize_gitlink_text(object_id: str) -> str:
    oid = require_object_id(object_id, field="gitlink")
    return f"Subproject commit {oid}\n"


def decode_blob_bytes(
    data: bytes,
    *,
    path: str,
    ref: str,
    max_file_size_bytes: int,
) -> FileContentResult:
    size = len(data)
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
        return FileContentAvailable(text=data.decode("utf-8"))
    except UnicodeDecodeError:
        return FileContentUnavailable(
            reason=FileContentUnavailableReason.CONTENT_DECODE_FAILED,
            path=path,
            ref=ref,
            observed_size=size,
        )


def parse_tree_item(raw: object, *, ref: str) -> GitLabTreeEntry | None:
    """Parse one repository_tree item; skip directories."""
    if isinstance(raw, dict):
        path = raw.get("path")
        mode = raw.get("mode")
        otype = raw.get("type")
        oid = raw.get("id")
    else:
        path = getattr(raw, "path", None)
        mode = getattr(raw, "mode", None)
        otype = getattr(raw, "type", None)
        oid = getattr(raw, "id", None)
    if not isinstance(path, str) or not path:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message="Tree entry missing path",
        )
    mode_s = require_git_mode(mode, field=path)
    type_e = parse_object_type(otype)
    object_id = require_object_id(oid, field=path)
    if mode_s == MODE_TREE or type_e is GitLabObjectType.TREE:
        return None
    if mode_s not in _LEAF_MODES:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=path,
            message=f"Unsupported tree mode {mode_s}",
            observed=mode_s,
        )
    if mode_s in _REGULAR_BLOB_MODES and type_e is not GitLabObjectType.BLOB:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=path,
            message="Regular mode requires blob type",
        )
    if mode_s == MODE_SYMLINK and type_e is not GitLabObjectType.BLOB:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=path,
            message="Symlink mode requires blob type",
        )
    if mode_s == MODE_GITLINK and type_e is not GitLabObjectType.COMMIT:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            path=path,
            message="Gitlink mode requires commit type",
        )
    return GitLabTreeEntry(path=path, mode=mode_s, object_type=type_e, object_id=object_id, ref=ref)


def index_tree_entries(entries: list[GitLabTreeEntry]) -> dict[str, GitLabTreeEntry]:
    indexed: dict[str, GitLabTreeEntry] = {}
    for entry in entries:
        if entry.path in indexed:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
                path=entry.path,
                message="Ambiguous duplicate tree path",
            )
        indexed[entry.path] = entry
    return indexed


def require_tree_entry(tree: dict[str, GitLabTreeEntry], path: str, *, ref: str) -> GitLabTreeEntry:
    entry = tree.get(path)
    if entry is None:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
            path=path,
            message=f"Selected path missing from tree at {ref}",
        )
    return entry


def load_repository_tree_entries(project: object, *, ref: str) -> dict[str, GitLabTreeEntry]:
    """Load complete recursive tree via project.repository_tree(get_all=True)."""
    tree_ref = str(ref)
    if not tree_ref:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message="Empty tree ref",
        )
    repository_tree = getattr(project, "repository_tree", None)
    if not callable(repository_tree):
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message="Project does not support repository_tree",
        )
    try:
        raw_list = repository_tree(ref=tree_ref, recursive=True, get_all=True)
    except FullDiffIncompleteError:
        raise
    except TypeError:
        # Some fakes/SDK variants use ``all=True`` instead of ``get_all=True``.
        raw_list = repository_tree(ref=tree_ref, recursive=True, all=True)

    if raw_list is None:
        raw_list = []
    if not isinstance(raw_list, (list, tuple)):
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message="repository_tree did not return a list",
        )

    entries: list[GitLabTreeEntry] = []
    for raw in raw_list:
        parsed = parse_tree_item(raw, ref=str(ref))
        if parsed is not None:
            entries.append(parsed)
    return index_tree_entries(entries)


def resolve_entry_text(
    entry: GitLabTreeEntry,
    *,
    blob_bytes: bytes | None,
    max_file_size_bytes: int,
) -> FileContentAvailable:
    """Normalize tree-proven entry to available text (raises E5020 on failure)."""
    if entry.mode == MODE_GITLINK:
        return FileContentAvailable(text=synthesize_gitlink_text(entry.object_id))

    if entry.mode == MODE_SYMLINK or entry.mode in _REGULAR_BLOB_MODES:
        if blob_bytes is None:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
                path=entry.path,
                message="Missing blob bytes for tree entry",
            )
        decoded = decode_blob_bytes(
            blob_bytes,
            path=entry.path,
            ref=entry.ref,
            max_file_size_bytes=max_file_size_bytes,
        )
        if isinstance(decoded, FileContentAvailable):
            return decoded
        reason_map = {
            FileContentUnavailableReason.BINARY_CONTENT: FullDiffIncompleteReason.BINARY_CONTENT,
            FileContentUnavailableReason.FILE_SIZE_LIMIT: FullDiffIncompleteReason.FILE_SIZE_LIMIT,
            FileContentUnavailableReason.CONTENT_DECODE_FAILED: FullDiffIncompleteReason.CONTENT_DECODE_FAILED,
            FileContentUnavailableReason.NOT_FOUND: FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
            FileContentUnavailableReason.DIRECTORY: FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
        }
        raise FullDiffIncompleteError(
            reason_map.get(decoded.reason, FullDiffIncompleteReason.CONTENT_UNAVAILABLE),
            path=entry.path,
            observed=decoded.observed_size,
        )

    raise FullDiffIncompleteError(
        FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
        path=entry.path,
        message=f"Cannot resolve text for mode {entry.mode}",
        observed=entry.mode,
    )


def fetch_raw_blob_bytes(project: object, object_id: str) -> bytes:
    """Fetch raw blob bytes by object id (repository_raw_blob)."""
    oid = require_object_id(object_id, field="blob")
    raw_blob = getattr(project, "repository_raw_blob", None)
    if not callable(raw_blob):
        # Fallback attribute name used by some SDK versions
        raw_blob = getattr(project, "repository_blob", None)
        if not callable(raw_blob):
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
                message="Project does not support repository_raw_blob",
            )
        payload = raw_blob(oid)
        if isinstance(payload, dict):
            content = payload.get("content")
            encoding = payload.get("encoding")
            if encoding == "base64" and isinstance(content, str):
                import base64

                return base64.b64decode(content)
            if isinstance(content, str):
                return content.encode("utf-8")
        if isinstance(payload, (bytes, bytearray)):
            return bytes(payload)
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
            message="Unexpected blob payload",
        )

    data = raw_blob(oid)
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("utf-8")
    raise FullDiffIncompleteError(
        FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
        message="repository_raw_blob returned non-bytes",
    )


def mode_uses_raw_file_api(mode: str | None) -> bool:
    """True when ``files.raw`` is appropriate (tree-proven regular blobs only)."""
    return mode in _REGULAR_BLOB_MODES or mode is None
