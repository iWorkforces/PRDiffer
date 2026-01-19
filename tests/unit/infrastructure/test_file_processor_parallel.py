import pytest

from ccpragents.infrastructure.github.file_processor import FileProcessor


class DummyAPIService:
    def get_files_content_batch(self, repository, file_paths, branch):
        return {path: "" for path in file_paths}

    def get_files_content_batch_parallel(self, repository, file_paths, branch, max_workers=4):
        return {path: "" for path in file_paths}


class DummyPatternMatcher:
    def is_valid_file(self, filename: str) -> bool:
        return True


class DummyDiffUtils:
    def extend_patch(self, original_file_str: str, patch_str: str, new_file_str: str = "") -> str:
        return patch_str


class FakeFile:
    def __init__(self, filename: str):
        self.filename = filename
        self.status = "modified"
        self.patch = "@@ -1 +1 @@\n-line\n+line"
        self.additions = 1
        self.deletions = 1


def test_file_processor_uses_parallel_fetch(monkeypatch):
    processor = FileProcessor(
        github_api_service=DummyAPIService(),
        pattern_matcher=DummyPatternMatcher(),
        diff_utils=DummyDiffUtils(),
        parallel_fetch_threshold=2,
        max_parallel_workers=2,
    )

    called = {"parallel": False}

    def fake_parallel(*args, **kwargs):
        called["parallel"] = True
        return []

    monkeypatch.setattr(processor, "_process_files_with_content_parallel", fake_parallel)
    monkeypatch.setattr(
        processor,
        "_process_files_with_content",
        lambda *args, **kwargs: pytest.fail("Sequential path should not be used"),
    )

    files = [FakeFile("a.py"), FakeFile("b.py"), FakeFile("c.py")]
    processor.process_files_to_patches(files, repository=object(), head_sha="head", base_sha="base")

    assert called["parallel"] is True
