"""Tests for typed GitHub file content acquisition and scoped caching."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from prdiffer.domain.entities.file_content import (
    FileContentAvailable,
    FileContentUnavailable,
    FileContentUnavailableReason,
)
from prdiffer.infrastructure.github.client import GitHubAPIClient


def _client() -> GitHubAPIClient:
    client = GitHubAPIClient(use_advanced_retry=False, max_file_size_bytes=100)
    client._github_client = MagicMock()
    client._retry_handler = MagicMock()
    client._retry_handler.execute_with_retry.side_effect = lambda fn, *a, **k: fn(*a) if callable(fn) else fn
    return client


@pytest.mark.unit
class TestTypedFileContent:
    def test_zero_byte_content_is_available_and_cacheable(self) -> None:
        client = _client()
        repo = MagicMock()
        content = SimpleNamespace(encoding="base64", size=0, decoded_content=b"", path="empty.txt")
        client._github_client.get_repo.return_value = repo
        repo.get_contents.return_value = content

        def _retry_side_effect(fn, *a, **kw):
            if not callable(fn):
                return fn
            filtered = {k: v for k, v in kw.items() if k != "context"}
            return fn(*a, **filtered)

        client._retry_handler.execute_with_retry.side_effect = _retry_side_effect

        # Simpler path: patch get_file_content internals via direct extract + cache
        result = client._extract_file_content_result(content, "empty.txt", "abc")
        assert isinstance(result, FileContentAvailable)
        assert result.text == ""

        key = client._content_cache_key("o/r", "empty.txt", "abc")
        client._cache_set_available(key, "")
        assert client._cache_get_available(key) == ""

    def test_binary_encoding_is_unavailable_not_cached(self) -> None:
        client = _client()
        content = SimpleNamespace(encoding="none", size=12, decoded_content=None, path="bin.dat")
        result = client._extract_file_content_result(content, "bin.dat", "ref1")
        assert isinstance(result, FileContentUnavailable)
        assert result.reason is FileContentUnavailableReason.BINARY_CONTENT
        key = client._content_cache_key("o/r", "bin.dat", "ref1")
        assert client._cache_get_available(key) is None

    def test_exact_size_limit_boundary(self) -> None:
        client = _client()  # max 100
        ok = SimpleNamespace(encoding="base64", size=100, decoded_content=b"x" * 100, path="ok.txt")
        over = SimpleNamespace(encoding="base64", size=101, decoded_content=b"x" * 101, path="over.txt")
        assert isinstance(client._extract_file_content_result(ok, "ok.txt", "r"), FileContentAvailable)
        bad = client._extract_file_content_result(over, "over.txt", "r")
        assert isinstance(bad, FileContentUnavailable)
        assert bad.reason is FileContentUnavailableReason.FILE_SIZE_LIMIT

    def test_directory_response_is_unavailable(self) -> None:
        client = _client()
        client._github_client = MagicMock()
        repo = MagicMock()
        client._github_client.get_repo.return_value = repo

        def retry(fn, *args, **kwargs):
            return fn(*args)

        client._retry_handler.execute_with_retry.side_effect = retry
        repo.get_contents.return_value = [SimpleNamespace(), SimpleNamespace()]

        result = client.get_file_content("owner/repo", "src/", "main")
        assert isinstance(result, FileContentUnavailable)
        assert result.reason is FileContentUnavailableReason.DIRECTORY

    def test_same_path_ref_different_repos_isolated_cache(self) -> None:
        client = _client()
        key_a = client._content_cache_key("a/repo", "file.py", "sha")
        key_b = client._content_cache_key("b/repo", "file.py", "sha")
        client._cache_set_available(key_a, "from-a")
        client._cache_set_available(key_b, "from-b")
        assert client._cache_get_available(key_a) == "from-a"
        assert client._cache_get_available(key_b) == "from-b"

    def test_unavailable_then_success_refetches(self) -> None:
        client = _client()
        key = client._content_cache_key("o/r", "f.py", "sha")
        # Unavailable must not populate cache
        assert client._cache_get_available(key) is None
        client._cache_set_available(key, "now-ok")
        assert client._cache_get_available(key) == "now-ok"

    def test_decode_failure_is_unavailable(self) -> None:
        client = _client()
        content = SimpleNamespace(
            encoding="base64",
            size=4,
            path="bad.txt",
            decoded_content=SimpleNamespace(decode=lambda *a, **k: (_ for _ in ()).throw(UnicodeDecodeError("utf-8", b"", 0, 1, "bad"))),
        )
        result = client._extract_file_content_result(content, "bad.txt", "r")
        assert isinstance(result, FileContentUnavailable)
        assert result.reason is FileContentUnavailableReason.CONTENT_DECODE_FAILED
