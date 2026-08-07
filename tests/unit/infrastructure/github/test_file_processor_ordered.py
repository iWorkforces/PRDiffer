"""Ordered strict FileProcessor assembly tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from prdiffer.domain.entities.file_content import FileContentAvailable
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.infrastructure.github.file_processor import FileProcessor


class AcceptAllMatcher:
    def is_valid_file(self, filename: str) -> bool:
        return True


def _file(
    name: str,
    status: str,
    *,
    previous: str | None = None,
    patch: str | None = "@@",
    additions: int = 1,
    deletions: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        filename=name,
        status=status,
        previous_filename=previous,
        patch=patch,
        additions=additions,
        deletions=deletions,
    )


@pytest.fixture
def processor() -> FileProcessor:
    api = MagicMock()
    api.get_files_content_batch.side_effect = lambda repo, paths, ref: {path: FileContentAvailable(text=f"{ref}:{path}\n") for path in paths}
    return FileProcessor(
        github_api_service=api,
        pattern_matcher=AcceptAllMatcher(),
        diff_utils=MagicMock(),
        max_files_allowed=50,
        # Unit tests mock the batch API; keep head/base sequential for determinism.
        parallel_head_base_fetch_enabled=False,
        require_git_tree=False,
    )


@pytest.mark.unit
class TestOrderedAssembly:
    def test_mixed_statuses_preserve_order(self, processor: FileProcessor) -> None:
        files = [
            _file("mod.py", "modified"),
            _file("del.py", "removed", deletions=1),
            _file("new.py", "renamed", previous="old.py"),
            _file("add.py", "added"),
        ]

        # rename-only: same content both sides via controlled API
        def batch(repo, paths, ref):
            out = {}
            for path in paths:
                if path in ("old.py", "new.py"):
                    out[path] = FileContentAvailable(text="same\n")
                else:
                    out[path] = FileContentAvailable(text=f"{ref}:{path}\n")
            return out

        processor._github_api_service.get_files_content_batch.side_effect = batch
        repo = SimpleNamespace(full_name="o/r")
        result = processor.process_files_to_patches(files, repo, "head", "base")  # cast via SimpleNamespace duck typing

        assert [p.filename for p in result] == ["mod.py", "del.py", "new.py", "add.py"]
        assert [p.edit_type for p in result] == [
            EDIT_TYPE.MODIFIED,
            EDIT_TYPE.DELETED,
            EDIT_TYPE.RENAMED,
            EDIT_TYPE.ADDED,
        ]
        assert result[1].base_file == "base:del.py\n"
        assert result[1].head_file == ""
        assert result[2].old_filename == "old.py"
        assert result[3].base_file == ""
        assert result[3].head_file.startswith("head:")

    def test_unknown_status_rejected(self, processor: FileProcessor) -> None:
        files = [_file("x.py", "copied")]
        with pytest.raises(FullDiffIncompleteError) as exc:
            processor.process_files_to_patches(files, SimpleNamespace(full_name="o/r"), "h", "b")
        assert exc.value.reason is FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS

    def test_sync_async_parity(self, processor: FileProcessor) -> None:
        import anyio

        files = [
            _file("a.py", "modified"),
            _file("b.py", "added"),
        ]
        repo = SimpleNamespace(full_name="o/r")
        sync_result = processor.process_files_to_patches(files, repo, "h", "b")

        async def run_async():
            return await processor.process_files_to_patches_async(files, repo, "h", "b")

        async_result = anyio.run(run_async)
        assert [p.filename for p in sync_result] == [p.filename for p in async_result]
        assert [p.edit_type for p in sync_result] == [p.edit_type for p in async_result]


def test_require_git_tree_fails_closed_without_tree_api() -> None:
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    import pytest
    from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
    from prdiffer.infrastructure.github.file_processor import FileProcessor

    api = MagicMock()
    proc = FileProcessor(
        github_api_service=api,
        pattern_matcher=MagicMock(is_valid_file=lambda p: True),
        diff_utils=MagicMock(),
        require_git_tree=True,
    )
    files = [SimpleNamespace(filename="a.py", status="modified", patch="", additions=1, deletions=0)]
    with pytest.raises(FullDiffIncompleteError) as ei:
        proc.process_files_to_patches(files, SimpleNamespace(full_name="o/r"), "h" * 40, "b" * 40)
    assert ei.value.reason is FullDiffIncompleteReason.INVENTORY_TRUNCATED
    api.get_files_content_batch.assert_not_called()


def test_rename_without_previous_filename_fails_before_content(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    import pytest
    from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
    from prdiffer.infrastructure.github.file_processor import FileProcessor

    api = MagicMock()
    proc = FileProcessor(
        github_api_service=api,
        pattern_matcher=MagicMock(is_valid_file=lambda p: True),
        diff_utils=MagicMock(),
    )
    files = [SimpleNamespace(filename="new.py", status="renamed", previous_filename=None, patch="")]
    with pytest.raises(FullDiffIncompleteError) as ei:
        proc.process_files_to_patches(files, SimpleNamespace(full_name="o/r"), "h" * 40, "b" * 40)
    assert ei.value.reason is FullDiffIncompleteReason.UNSUPPORTED_FILE_STATUS
    api.get_files_content_batch.assert_not_called()
    api.get_files_content_multi_ref_batch.assert_not_called()


def test_tree_path_assembles_modes_and_gitlink_without_contents_api():
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from prdiffer.domain.entities.file_patch import EDIT_TYPE
    from prdiffer.infrastructure.github.file_processor import FileProcessor

    oid_blob = "1" * 40
    oid_link = "2" * 40
    base = "b" * 40
    head = "c" * 40

    def get_git_tree(sha, recursive=False):
        if sha == head:
            items = [
                SimpleNamespace(path="sub", mode="160000", type="commit", sha=oid_link),
                SimpleNamespace(path="a.py", mode="100644", type="blob", sha=oid_blob),
            ]
        else:
            items = [
                SimpleNamespace(path="a.py", mode="100644", type="blob", sha=oid_blob),
            ]
        return SimpleNamespace(truncated=False, tree=items)

    def get_git_blob(sha):
        assert sha == oid_blob
        return SimpleNamespace(encoding="utf-8", content="hello\n", decoded_content=b"hello\n")

    repo = SimpleNamespace(full_name="o/r", get_git_tree=get_git_tree, get_git_blob=get_git_blob)
    api = MagicMock()
    proc = FileProcessor(
        github_api_service=api,
        pattern_matcher=MagicMock(is_valid_file=lambda p: True),
        diff_utils=MagicMock(),
    )
    files = [
        SimpleNamespace(filename="a.py", status="modified", patch="", additions=1, deletions=0),
        SimpleNamespace(filename="sub", status="added", patch="", additions=1, deletions=0),
    ]
    patches = proc.process_files_to_patches(files, repo, head, base)
    assert len(patches) == 2
    assert patches[0].edit_type is EDIT_TYPE.MODIFIED
    assert patches[0].base_file == "hello\n"
    assert patches[0].head_file == "hello\n"
    assert patches[0].old_mode == "100644"
    assert patches[0].new_mode == "100644"
    assert patches[1].edit_type is EDIT_TYPE.ADDED
    assert patches[1].head_file == f"Subproject commit {oid_link}\n"
    assert patches[1].new_mode == "160000"
    api.get_files_content_batch.assert_not_called()
