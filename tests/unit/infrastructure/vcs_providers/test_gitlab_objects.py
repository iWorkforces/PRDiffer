"""Unit tests for GitLab immutable tree/object helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from prdiffer.domain.entities.file_content import FileContentAvailable
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.infrastructure.vcs_providers.gitlab_objects import (
    MODE_GITLINK,
    MODE_REGULAR_FILE,
    MODE_SYMLINK,
    GitLabObjectType,
    GitLabTreeEntry,
    decode_blob_bytes,
    index_tree_entries,
    load_repository_tree_entries,
    require_tree_entry,
    resolve_entry_text,
    synthesize_gitlink_text,
)

OID = "a" * 40
OID2 = "b" * 40
REF = "c" * 40


def _entry(
    path: str = "f.txt",
    *,
    mode: str = MODE_REGULAR_FILE,
    otype: GitLabObjectType = GitLabObjectType.BLOB,
    oid: str = OID,
) -> GitLabTreeEntry:
    return GitLabTreeEntry(path=path, mode=mode, object_type=otype, object_id=oid, ref=REF)


class TestDecodeAndGitlink:
    def test_zero_byte_available(self) -> None:
        result = decode_blob_bytes(b"", path="a", ref=REF, max_file_size_bytes=10)
        assert isinstance(result, FileContentAvailable)
        assert result.text == ""

    def test_gitlink_text(self) -> None:
        assert synthesize_gitlink_text(OID) == f"Subproject commit {OID}\n"


class TestTreeIndex:
    def test_load_skips_directories(self) -> None:
        items = [
            SimpleNamespace(path="a.py", mode="100644", type="blob", id=OID),
            SimpleNamespace(path="d", mode="040000", type="tree", id=OID2),
            SimpleNamespace(path="sub", mode="160000", type="commit", id=OID2),
            SimpleNamespace(path="link", mode="120000", type="blob", id=OID),
        ]
        project = SimpleNamespace(repository_tree=lambda **kwargs: items)
        tree = load_repository_tree_entries(project, ref=REF)
        assert set(tree) == {"a.py", "sub", "link"}
        assert tree["sub"].mode == MODE_GITLINK

    def test_load_rejects_incomplete_paginator(self) -> None:
        items = [SimpleNamespace(path="a.py", mode="100644", type="blob", id=OID)]

        class PartialPage(list):
            next_page = 2

        project = SimpleNamespace(repository_tree=lambda **kwargs: PartialPage(items))
        with pytest.raises(FullDiffIncompleteError) as ei:
            load_repository_tree_entries(project, ref=REF)
        assert ei.value.reason is FullDiffIncompleteReason.INVENTORY_TRUNCATED

    def test_missing_path(self) -> None:
        tree = index_tree_entries([_entry("a.py")])
        with pytest.raises(FullDiffIncompleteError) as ei:
            require_tree_entry(tree, "missing", ref=REF)
        assert ei.value.reason is FullDiffIncompleteReason.CONTENT_UNAVAILABLE


class TestResolve:
    def test_symlink_from_blob(self) -> None:
        entry = _entry(path="l", mode=MODE_SYMLINK)
        text = resolve_entry_text(entry, blob_bytes=b"../t", max_file_size_bytes=100)
        assert text.text == "../t"

    def test_gitlink_no_blob(self) -> None:
        entry = _entry(path="s", mode=MODE_GITLINK, otype=GitLabObjectType.COMMIT, oid=OID2)
        text = resolve_entry_text(entry, blob_bytes=None, max_file_size_bytes=100)
        assert text.text == f"Subproject commit {OID2}\n"
