"""Unit tests for ETag adapter."""

import time
import pytest
from prdiffer.infrastructure.github.etag_adapter import ETagRequestAdapter


@pytest.fixture
def etag_adapter():
    """Create ETag adapter for testing."""
    return ETagRequestAdapter(
        enabled=True,
        etag_ttl=600,
        etag_cache_size=1000,
    )


class TestETagAdapterInitialization:
    """Test ETag adapter initialization."""

    def test_adapter_enabled(self, etag_adapter):
        """Test adapter is enabled by default."""
        assert etag_adapter.is_enabled() is True

    def test_adapter_disabled_initialization(self):
        """Test adapter can be initialized disabled."""
        adapter = ETagRequestAdapter(enabled=False)
        assert adapter.is_enabled() is False

    def test_adapter_cache_empty_on_init(self, etag_adapter):
        """Test adapter cache is empty on initialization."""
        stats = etag_adapter.get_stats()
        assert stats["cache_size"] == 0


class TestETagStorage:
    """Test ETag storage and retrieval."""

    def test_get_etag_miss(self, etag_adapter):
        """Test ETag miss when cache is empty."""
        etag = etag_adapter._get_etag("http://example.com/file.txt")
        assert etag is None

    def test_store_and_get_etag(self, etag_adapter):
        """Test storing and retrieving ETag."""
        url = "http://example.com/file.txt"
        etag = '"abc123"'

        etag_adapter._store_etag(url, etag, "file content")
        retrieved = etag_adapter._get_etag(url)

        assert retrieved == etag

    def test_store_etag_with_content(self, etag_adapter):
        """Test storing ETag with content."""
        url = "http://example.com/file.txt"
        etag = '"abc123"'
        content = "file content"

        etag_adapter._store_etag(url, etag, content)
        retrieved_content = etag_adapter._get_cached_content(url)

        assert retrieved_content == content

    def test_etag_miss_after_ttl(self, etag_adapter):
        """Test ETag expires after TTL."""
        url = "http://example.com/file.txt"
        etag = '"abc123"'

        adapter = ETagRequestAdapter(enabled=True, etag_ttl=1)
        adapter._store_etag(url, etag, "file content")

        time.sleep(1.5)

        retrieved = adapter._get_etag(url)
        assert retrieved is None

    def test_multiple_etags_stored(self, etag_adapter):
        """Test multiple ETags can be stored."""
        urls = [
            "http://example.com/file1.txt",
            "http://example.com/file2.txt",
            "http://example.com/file3.txt",
        ]

        for url in urls:
            etag_adapter._store_etag(url, f'"{url}"', f"content of {url}")

        for url in urls:
            retrieved = etag_adapter._get_etag(url)
            assert retrieved == f'"{url}"'


class TestETagCacheEviction:
    """Test ETag cache eviction."""

    def test_cache_size_limit(self):
        """Test cache evicts oldest entries when size limit reached."""
        adapter = ETagRequestAdapter(enabled=True, etag_cache_size=2, etag_ttl=600)

        adapter._store_etag("url1", "etag1", "content1")
        adapter._store_etag("url2", "etag2", "content2")
        adapter._store_etag("url3", "etag3", "content3")

        stats = adapter.get_stats()
        assert stats["cache_size"] == 2

        etag1 = adapter._get_etag("url1")
        assert etag1 is None

        etag2 = adapter._get_etag("url2")
        assert etag2 == "etag2"

    def test_clear_cache(self, etag_adapter):
        """Test cache can be cleared."""
        url = "http://example.com/file.txt"
        etag = '"abc123"'

        etag_adapter._store_etag(url, etag, "file content")
        assert etag_adapter.get_stats()["cache_size"] == 1

        etag_adapter.clear_cache()
        assert etag_adapter.get_stats()["cache_size"] == 0

    def test_ttl_eviction(self):
        """Test expired entries are evicted."""
        adapter = ETagRequestAdapter(enabled=True, etag_cache_size=1000, etag_ttl=1)

        url1 = "http://example.com/file1.txt"
        url2 = "http://example.com/file2.txt"

        adapter._store_etag(url1, "etag1", "content1")
        time.sleep(1)
        adapter._store_etag(url2, "etag2", "content2")

        time.sleep(1)

        etag1 = adapter._get_etag(url1)
        assert etag1 is None

        etag2 = adapter._get_etag(url2)
        assert etag2 is None


class TestETagAdapterStatistics:
    """Test ETag adapter statistics."""

    def test_initial_stats(self, etag_adapter):
        """Test initial statistics."""
        stats = etag_adapter.get_stats()

        assert stats["enabled"] is True
        assert stats["cache_size"] == 0
        assert stats["etag_hits"] == 0
        assert stats["etag_misses"] == 0
        assert stats["not_modified_responses"] == 0
        assert stats["hit_rate_percent"] == 0

    def test_stats_after_operations(self, etag_adapter):
        """Test statistics are updated after operations."""
        url = "http://example.com/file.txt"

        etag_adapter._get_etag(url)
        etag_adapter._get_etag(url)

        etag_adapter._store_etag(url, '"abc123"', "content")
        etag_adapter._get_etag(url)

        stats = etag_adapter.get_stats()

        assert stats["etag_hits"] == 1
        assert stats["etag_misses"] == 2


class TestETagResponseHandling:
    """Test ETag response handling."""

    def test_add_if_none_match_header_with_etag(self, etag_adapter):
        """Test If-None-Match header is added when ETag cached."""
        url = "http://example.com/file.txt"
        etag = '"abc123"'

        etag_adapter._store_etag(url, etag, "content")

        headers = {}
        updated_headers = etag_adapter.add_if_none_match_header(url, headers)

        assert "If-None-Match" in updated_headers
        assert updated_headers["If-None-Match"] == etag

    def test_add_if_none_match_header_without_etag(self, etag_adapter):
        """Test If-None-Match header is not added when no ETag cached."""
        url = "http://example.com/file.txt"

        headers = {}
        updated_headers = etag_adapter.add_if_none_match_header(url, headers)

        assert "If-None-Match" not in updated_headers

    def test_handle_200_response_stores_etag(self, etag_adapter):
        """Test ETag is stored on 200 response."""
        url = "http://example.com/file.txt"
        etag = '"abc123"'
        content = "file content"

        result = etag_adapter.handle_etag_response(url, 200, {"ETag": etag}, content)

        assert result == content
        retrieved_etag = etag_adapter._get_etag(url)
        assert retrieved_etag == etag

    def test_handle_304_response_returns_cached_content(self, etag_adapter):
        """Test 304 response returns cached content."""
        url = "http://example.com/file.txt"
        etag = '"abc123"'
        content = "file content"

        etag_adapter._store_etag(url, etag, content)

        result = etag_adapter.handle_etag_response(url, 304, {"ETag": etag}, "")

        assert result == content

    def test_handle_304_without_cached_content(self, etag_adapter):
        """Test 304 response returns empty string when no cached content."""
        url = "http://example.com/file.txt"
        etag = '"abc123"'

        etag_adapter._store_etag(url, etag, None)

        result = etag_adapter.handle_etag_response(url, 304, {"ETag": etag}, "")

        assert result == ""

    def test_not_modified_count_increases(self, etag_adapter):
        """Test not_modified_responses count increases on 304."""
        url = "http://example.com/file.txt"
        etag = '"abc123"'
        content = "file content"

        etag_adapter._store_etag(url, etag, content)
        etag_adapter.handle_etag_response(url, 304, {"ETag": etag}, "")

        stats = etag_adapter.get_stats()
        assert stats["not_modified_responses"] == 1

    def test_disabled_adapter_no_operations(self):
        """Test disabled adapter does not perform operations."""
        adapter = ETagRequestAdapter(enabled=False)

        url = "http://example.com/file.txt"
        headers = {}

        updated_headers = adapter.add_if_none_match_header(url, headers)
        assert "If-None-Match" not in updated_headers

        adapter._store_etag(url, '"abc123"', "content")
        assert adapter.get_stats()["cache_size"] == 0
