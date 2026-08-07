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


def parse_tree_entry_from_provider(raw: object, *, ref: str) -> GitTreeEntry | None:
    """Parse one recursive tree item; skip pure directory leaves for path index.

    Directory entries (mode 040000 / type tree) are ignored for content maps.
    Truncation and malformed leaf entries raise E5020.
    """
    path = getattr(raw, "path", None)
    mode = getattr(raw, "mode", None)
    otype = getattr(raw, "type", None)
    sha = getattr(raw, "sha", None)
    if path is None and isinstance(raw, dict):
        path = raw.get("path")
        mode = raw.get("mode")
        otype = raw.get("type")
        sha = raw.get("sha")
    if not isinstance(path, str) or not path:
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS,
            message="Tree entry missing path",
        )
    try:
        mode_s = require_git_mode(mode, field=path)
        type_e = parse_git_object_type(otype)
        oid = require_object_id(sha, field=path)
    except FullDiffIncompleteError as exc:
        # Attach path when missing
        if "path" not in (exc.details or {}):
            raise FullDiffIncompleteError(exc.reason, path=path, message=str(exc), observed=exc.details.get("observed") if exc.details else None) from exc
        raise
    if mode_s == MODE_TREE or type_e is GitObjectType.TREE:
        return None
    entry = GitTreeEntry(path=path, mode=mode_s, object_type=type_e, object_id=oid, ref=ref)
    validate_tree_entry_consistency(entry)
    return entry


def load_recursive_tree_entries(repository: object, tree_sha: str) -> dict[str, GitTreeEntry]:
    """Load a recursive tree by immutable SHA; reject truncated responses."""
    ref = require_object_id(tree_sha, field="tree_sha")
    get_git_tree = getattr(repository, "get_git_tree", None)
    if not callable(get_git_tree):
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message="Repository does not support get_git_tree",
        )
    try:
        tree = get_git_tree(ref, recursive=True)
    except FullDiffIncompleteError:
        raise
    except Exception:
        # Operational errors propagate; do not remap to empty inventory.
        raise

    if bool(getattr(tree, "truncated", False)):
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message="Git tree response was truncated",
            observed="truncated",
        )

    raw_entries = getattr(tree, "tree", None)
    if raw_entries is None and isinstance(tree, dict):
        raw_entries = tree.get("tree")
    if raw_entries is None:
        raw_entries = []
    if not isinstance(raw_entries, (list, tuple)):
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.INVENTORY_TRUNCATED,
            message="Git tree payload missing tree list",
        )

    entries: list[GitTreeEntry] = []
    for raw in raw_entries:
        parsed = parse_tree_entry_from_provider(raw, ref=ref)
        if parsed is not None:
            entries.append(parsed)
    return index_tree_entries(entries)


def resolve_entry_text(
    entry: GitTreeEntry,
    *,
    blob_bytes: bytes | None,
    max_file_size_bytes: int,
) -> GitObjectText:
    """Normalize a tree-proven entry to text (regular/symlink/gitlink)."""
    if entry.mode == MODE_GITLINK:
        return GitObjectText(
            path=entry.path,
            ref=entry.ref,
            mode=entry.mode,
            object_id=entry.object_id,
            text=synthesize_gitlink_text(entry.object_id),
        )

    if entry.mode == MODE_SYMLINK or entry.mode in _REGULAR_BLOB_MODES:
        if blob_bytes is None:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
                path=entry.path,
                message="Missing blob bytes for tree entry",
            )
        decoded = decode_regular_blob_bytes(
            blob_bytes,
            path=entry.path,
            ref=entry.ref,
            max_file_size_bytes=max_file_size_bytes,
        )
        if isinstance(decoded, FileContentAvailable):
            return GitObjectText(
                path=entry.path,
                ref=entry.ref,
                mode=entry.mode,
                object_id=entry.object_id,
                text=decoded.text,
            )
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


def fetch_blob_bytes(repository: object, object_id: str) -> bytes:
    """Fetch raw blob bytes by object id (symlink and regular file support)."""
    oid = require_object_id(object_id, field="blob")
    get_git_blob = getattr(repository, "get_git_blob", None)
    if not callable(get_git_blob):
        raise FullDiffIncompleteError(
            FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
            message="Repository does not support get_git_blob",
        )
    blob = get_git_blob(oid)
    encoding = getattr(blob, "encoding", None)
    content = getattr(blob, "content", None)
    if encoding == "base64" and isinstance(content, str):
        import base64

        return base64.b64decode(content)
    data = getattr(blob, "decoded_content", None)
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(content, (bytes, bytearray)):
        return bytes(content)
    if isinstance(content, str):
        return content.encode("utf-8")
    raise FullDiffIncompleteError(
        FullDiffIncompleteReason.CONTENT_UNAVAILABLE,
        message="Blob payload missing decodable content",
        observed=str(encoding),
    )
