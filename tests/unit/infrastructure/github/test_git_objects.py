"""Unit tests for immutable GitHub git object helpers."""

from __future__ import annotations

import pytest

from prdiffer.domain.entities.file_content import FileContentAvailable, FileContentUnavailableReason
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.infrastructure.github.git_objects import (
    MODE_GITLINK,
    MODE_REGULAR_FILE,
    MODE_SYMLINK,
    GitObjectType,
    GitTreeEntry,
    decode_regular_blob_bytes,
    index_tree_entries,
    require_distinct_rename_previous,
    require_tree_entry,
    synthesize_gitlink_text,
    validate_tree_entry_consistency,
)

OID = "a" * 40
OID2 = "b" * 40
REF = "c" * 40


def _entry(
    path: str = "f.txt",
    *,
    mode: str = MODE_REGULAR_FILE,
    otype: GitObjectType = GitObjectType.BLOB,
    oid: str = OID,
    ref: str = REF,
) -> GitTreeEntry:
    return GitTreeEntry(path=path, mode=mode, object_type=otype, object_id=oid, ref=ref)


class TestGitTreeEntryValidation:
    def test_rejects_bad_mode(self) -> None:
        with pytest.raises(ValueError):
            GitTreeEntry(path="a", mode="10064", object_type=GitObjectType.BLOB, object_id=OID, ref=REF)

    def test_normalizes_object_id_case(self) -> None:
        entry = GitTreeEntry(
            path="a",
            mode=MODE_REGULAR_FILE,
            object_type=GitObjectType.BLOB,
            object_id="A" * 40,
            ref=REF,
        )
        assert entry.object_id == "a" * 40


class TestModeTypeConsistency:
    def test_symlink_requires_blob(self) -> None:
        entry = _entry(mode=MODE_SYMLINK, otype=GitObjectType.COMMIT)
        with pytest.raises(FullDiffIncompleteError) as ei:
            validate_tree_entry_consistency(entry)
        assert ei.value.reason is FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS

    def test_gitlink_requires_commit(self) -> None:
        entry = _entry(mode=MODE_GITLINK, otype=GitObjectType.BLOB)
        with pytest.raises(FullDiffIncompleteError) as ei:
            validate_tree_entry_consistency(entry)
        assert ei.value.reason is FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS


class TestDecodeRegularBlob:
    def test_zero_byte_available(self) -> None:
        result = decode_regular_blob_bytes(b"", path="a", ref=REF, max_file_size_bytes=10)
        assert isinstance(result, FileContentAvailable)
        assert result.text == ""

    def test_nul_is_binary(self) -> None:
        result = decode_regular_blob_bytes(b"a\x00b", path="a", ref=REF, max_file_size_bytes=10)
        assert not isinstance(result, FileContentAvailable)
        assert result.reason is FileContentUnavailableReason.BINARY_CONTENT

    def test_invalid_utf8(self) -> None:
        result = decode_regular_blob_bytes(b"\xff\xfe", path="a", ref=REF, max_file_size_bytes=10)
        assert not isinstance(result, FileContentAvailable)
        assert result.reason is FileContentUnavailableReason.CONTENT_DECODE_FAILED

    def test_oversize(self) -> None:
        result = decode_regular_blob_bytes(b"abcd", path="a", ref=REF, max_file_size_bytes=3)
        assert not isinstance(result, FileContentAvailable)
        assert result.reason is FileContentUnavailableReason.FILE_SIZE_LIMIT


class TestGitlinkAndRename:
    def test_synthesize_gitlink_text(self) -> None:
        assert synthesize_gitlink_text(OID) == f"Subproject commit {OID}\n"

    def test_rename_requires_distinct_previous(self) -> None:
        assert require_distinct_rename_previous("old.py", "new.py") == "old.py"
        with pytest.raises(FullDiffIncompleteError) as ei:
            require_distinct_rename_previous(None, "new.py")
        assert ei.value.reason is FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS
        with pytest.raises(FullDiffIncompleteError):
            require_distinct_rename_previous("same.py", "same.py")


class TestTreeIndex:
    def test_duplicate_path_rejected(self) -> None:
        with pytest.raises(FullDiffIncompleteError) as ei:
            index_tree_entries([_entry("a.py"), _entry("a.py", oid=OID2)])
        assert ei.value.reason is FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS

    def test_missing_path_is_content_unavailable(self) -> None:
        tree = index_tree_entries([_entry("a.py")])
        with pytest.raises(FullDiffIncompleteError) as ei:
            require_tree_entry(tree, "missing.py", ref=REF)
        assert ei.value.reason is FullDiffIncompleteReason.CONTENT_UNAVAILABLE
