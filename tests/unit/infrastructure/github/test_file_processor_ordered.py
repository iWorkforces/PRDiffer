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
