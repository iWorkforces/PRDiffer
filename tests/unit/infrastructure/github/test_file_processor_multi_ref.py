from __future__ import annotations

from types import SimpleNamespace

import pytest

from prdiffer.domain.entities.file_content import FileContentAvailable, FileContentRequest, FileContentResponse, FileContentResult
from prdiffer.infrastructure.github.file_processor import FileProcessor


class AcceptAllMatcher:
    def is_valid_file(self, filename: str) -> bool:
        return True


class RecordingContentAPI:
    def __init__(self) -> None:
        self.multi_ref_calls: list[tuple[FileContentRequest, ...]] = []
        self.single_ref_calls: list[tuple[str, tuple[str, ...], str]] = []

    def get_files_content_multi_ref_batch(self, requests: tuple[FileContentRequest, ...]) -> tuple[FileContentResponse, ...]:
        self.multi_ref_calls.append(requests)
        return tuple(FileContentResponse(request=request, content=FileContentAvailable(text=f"{request.ref}:{request.path}")) for request in requests)

    def get_files_content_batch(self, repo_full_name: str, paths: list[str], ref: str) -> dict[str, FileContentResult]:
        self.single_ref_calls.append((repo_full_name, tuple(paths), ref))
        return {path: FileContentAvailable(text=f"{ref}:{path}") for path in paths}


def _processor(api: RecordingContentAPI, *, enabled: bool) -> FileProcessor:
    return FileProcessor(
        github_api_service=api,
        pattern_matcher=AcceptAllMatcher(),
        diff_utils=SimpleNamespace(build_full_file_patch=lambda *_args: ""),
        parallel_head_base_fetch_enabled=enabled,
    )


def _file(path: str) -> SimpleNamespace:
    return SimpleNamespace(filename=path, status="modified", previous_filename=None, patch="@@", additions=1, deletions=1)


@pytest.mark.unit
def test_enabled_head_base_processing_uses_one_interleaved_multi_ref_batch_in_provider_order() -> None:
    api = RecordingContentAPI()
    result = _processor(api, enabled=True).process_files_to_patches(
        [_file("first.py"), _file("second.py")],
        SimpleNamespace(full_name="owner/repository"),
        "head",
        "base",
    )

    assert api.multi_ref_calls == [
        (
            FileContentRequest("owner/repository", "first.py", "head"),
            FileContentRequest("owner/repository", "first.py", "base"),
            FileContentRequest("owner/repository", "second.py", "head"),
            FileContentRequest("owner/repository", "second.py", "base"),
        )
    ]
    assert api.single_ref_calls == []
    assert [(patch.filename, patch.base_file, patch.head_file) for patch in result] == [
        ("first.py", "base:first.py", "head:first.py"),
        ("second.py", "base:second.py", "head:second.py"),
    ]


@pytest.mark.unit
def test_disabled_or_one_sided_head_base_processing_uses_sequential_single_ref_batches() -> None:
    api = RecordingContentAPI()
    processor = _processor(api, enabled=False)

    head, base = processor._fetch_head_base_batches("owner/repository", ["head.py"], ["base.py"], "head", "base")

    assert api.multi_ref_calls == []
    assert api.single_ref_calls == [
        ("owner/repository", ("head.py",), "head"),
        ("owner/repository", ("base.py",), "base"),
    ]
    assert head == {"head.py": FileContentAvailable(text="head:head.py")}
    assert base == {"base.py": FileContentAvailable(text="base:base.py")}


@pytest.mark.unit
def test_enabled_one_sided_head_base_processing_uses_single_ref_batch() -> None:
    api = RecordingContentAPI()

    head, base = _processor(api, enabled=True)._fetch_head_base_batches("owner/repository", ["added.py"], [], "head", "base")

    assert api.multi_ref_calls == []
    assert api.single_ref_calls == [("owner/repository", ("added.py",), "head")]
    assert head == {"added.py": FileContentAvailable(text="head:added.py")}
    assert base == {}
