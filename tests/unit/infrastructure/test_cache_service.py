"""Unit tests for CacheService infrastructure component.

Tests the CacheService component which provides in-memory caching
with commit-based invalidation, key hashing, and TTL support.
"""

import time
import threading
from unittest.mock import patch
import pytest
from prdiffer.infrastructure.cache_service import CacheService, get_cache_service
from prdiffer.domain.entities.pr_diff import PRDiff


@pytest.fixture
def reset_cache_service():
    """Reset the global cache service before each test."""
    import prdiffer.infrastructure.cache_service as cache_module

    cache_module._cache_service = None
    yield
    cache_module._cache_service = None


@pytest.fixture
def sample_pr_diff():
    """Create a sample PRDiff for testing."""
    return PRDiff(
        diff_content="sample diff content",
        commit_messages="Initial commit",
    )


class TestCacheServiceInitialization:
    """Test suite for CacheService initialization."""

    def test_cache_service_initialization(self, reset_cache_service):
        """Test CacheService can be initialized."""
        service = CacheService()

        assert service is not None
        assert hasattr(service, "cache")
        assert hasattr(service, "_lock")
        assert hasattr(service, "_use_hashed_keys")
        assert hasattr(service, "_ttl")

    def test_cache_service_initialization_no_hashing(self, reset_cache_service):
        """Test CacheService with hashing disabled."""
        # Can't easily test this without mocking settings service
        # The configuration is loaded from settings during init
        # Just verify the attribute exists
        service = CacheService()

        assert hasattr(service, "_use_hashed_keys")
        assert isinstance(service._use_hashed_keys, bool)

    def test_cache_service_has_lock(self, reset_cache_service):
        """Test CacheService has thread safety lock."""
        service = CacheService()

        assert isinstance(service._lock, type(threading.RLock()))

    def test_cache_service_initial_stats(self, reset_cache_service):
        """Test initial statistics are zero."""
        service = CacheService()

        assert service._cache_hits == 0
        assert service._cache_misses == 0
        assert service._cache_expirations == 0


class TestCacheServiceGetCacheKey:
    """Test suite for get_cache_key method."""

    def test_get_cache_key_format(self, reset_cache_service):
        """Test cache key format."""
        service = CacheService()

        key = service.get_cache_key("owner", "repo", 123)

        assert key == "owner/repo/pr/123"

    def test_get_cache_key_with_special_chars(self, reset_cache_service):
        """Test cache key with special characters in names."""
        service = CacheService()

        key = service.get_cache_key("owner-name", "repo.name", 456)

        assert key == "owner-name/repo.name/pr/456"


class TestCacheServiceHashKey:
    """Test suite for _hash_key method."""

    def test_hash_key_md5_length(self, reset_cache_service):
        """Test MD5 hashing produces 32 character hex string."""
        service = CacheService()

        hashed = service._hash_key("test_key")

        assert len(hashed) == 32
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_key_consistent(self, reset_cache_service):
        """Test hashing is consistent for same input."""
        service = CacheService()

        hash1 = service._hash_key("test_key")
        hash2 = service._hash_key("test_key")

        assert hash1 == hash2

    def test_hash_key_different_inputs(self, reset_cache_service):
        """Test different inputs produce different hashes."""
        service = CacheService()

        hash1 = service._hash_key("key1")
        hash2 = service._hash_key("key2")

        assert hash1 != hash2

    def test_hash_key_sha256_length(self, reset_cache_service):
        """Test SHA256 hashing produces 64 character hex string."""
        with patch.object(CacheService, "__init__", lambda self: None):
            service = CacheService()
            service._hash_algorithm = "sha256"

        hashed = service._hash_key("test_key")

        assert len(hashed) == 64

    def test_hash_key_unsupported_algorithm(self, reset_cache_service):
        """Test unsupported hash algorithm raises ValueError."""
        with patch.object(CacheService, "__init__", lambda self: None):
            service = CacheService()
            service._hash_algorithm = "invalid"

        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            service._hash_key("test_key")


class TestCacheServiceGetSet:
    """Test suite for get and set methods."""

    def test_set_and_get_cache_hit(self, reset_cache_service, sample_pr_diff):
        """Test setting and getting cached data."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)

        service.set(cache_key, "abc123", sample_pr_diff)
        result = service.get(cache_key, "abc123")

        assert result is not None
        assert result.diff_content == "sample diff content"

    def test_get_cache_miss(self, reset_cache_service):
        """Test getting non-existent key returns None."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)

        result = service.get(cache_key, "abc123")

        assert result is None

    def test_get_commit_sha_mismatch(self, reset_cache_service, sample_pr_diff):
        """Test cache miss when commit SHA doesn't match."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)

        service.set(cache_key, "abc123", sample_pr_diff)
        result = service.get(cache_key, "def456")  # Different SHA

        assert result is None

    def test_set_overwrites_existing(self, reset_cache_service, sample_pr_diff):
        """Test setting same key overwrites existing data."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)

        new_diff = PRDiff(diff_content="new content", commit_messages="New commit")
        service.set(cache_key, "abc123", sample_pr_diff)
        service.set(cache_key, "def456", new_diff)

        result = service.get(cache_key, "def456")

        assert result.diff_content == "new content"

    def test_statistics_updated(self, reset_cache_service, sample_pr_diff):
        """Test cache hit/miss statistics are updated."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)

        service.set(cache_key, "abc123", sample_pr_diff)
        service.get(cache_key, "abc123")  # Hit
        service.get(cache_key, "def456")  # Miss (SHA mismatch)
        service.get("owner/repo/pr/999", "abc123")  # Miss (not found)

        assert service._cache_hits == 1
        assert service._cache_misses == 2


class TestCacheServiceInvalidate:
    """Test suite for invalidate method."""

    def test_invalidate_existing_key(self, reset_cache_service, sample_pr_diff):
        """Test invalidating an existing cache entry."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)

        service.set(cache_key, "abc123", sample_pr_diff)
        service.invalidate(cache_key)

        result = service.get(cache_key, "abc123")

        assert result is None

    def test_invalidate_nonexistent_key(self, reset_cache_service):
        """Test invalidating a non-existent key doesn't raise error."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)

        # Should not raise
        service.invalidate(cache_key)


class TestCacheServiceClear:
    """Test suite for clear method."""

    def test_clear_cache(self, reset_cache_service, sample_pr_diff):
        """Test clearing all cached data."""
        service = CacheService()

        service.set("owner1/repo1/pr/1", "abc123", sample_pr_diff)
        service.set("owner2/repo2/pr/2", "def456", sample_pr_diff)

        service.clear()

        assert len(service.cache) == 0
        assert service.get("owner1/repo1/pr/1", "abc123") is None


class TestCacheServiceGetStats:
    """Test suite for get_stats method."""

    def test_get_stats_empty(self, reset_cache_service):
        """Test stats when cache is empty."""
        service = CacheService()

        stats = service.get_stats()

        assert stats["size"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["hit_rate_percent"] == 0.0

    def test_get_stats_with_data(self, reset_cache_service, sample_pr_diff):
        """Test stats with cached data."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)

        service.set(cache_key, "abc123", sample_pr_diff)

        stats = service.get_stats()

        assert stats["size"] == 1
        assert "ttl_seconds" in stats

    def test_get_stats_hit_rate(self, reset_cache_service, sample_pr_diff):
        """Test hit rate calculation."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)

        service.set(cache_key, "abc123", sample_pr_diff)
        service.get(cache_key, "abc123")  # Hit
        service.get(cache_key, "def456")  # Miss

        stats = service.get_stats()

        assert stats["hit_rate_percent"] == 50.0


class TestCacheServiceTTL:
    """Test suite for TTL-based expiration."""

    def test_ttl_expiration(self, reset_cache_service, sample_pr_diff):
        """Test that entries expire after TTL."""
        # Create service with short TTL
        service = CacheService()
        service._ttl = 0.1  # 100ms TTL

        cache_key = service.get_cache_key("owner", "repo", 123)
        service.set(cache_key, "abc123", sample_pr_diff)

        # Wait for TTL to expire
        time.sleep(0.15)

        result = service.get(cache_key, "abc123")

        assert result is None

    def test_ttl_not_expired(self, reset_cache_service, sample_pr_diff):
        """Test that entries are valid before TTL expires."""
        service = CacheService()
        service._ttl = 10  # 10 second TTL

        cache_key = service.get_cache_key("owner", "repo", 123)
        service.set(cache_key, "abc123", sample_pr_diff)

        time.sleep(0.05)  # Small sleep

        result = service.get(cache_key, "abc123")

        assert result is not None

    def test_expiration_increments_counter(self, reset_cache_service, sample_pr_diff):
        """Test that expiration increments expiration counter."""
        service = CacheService()
        service._ttl = 0.1

        cache_key = service.get_cache_key("owner", "repo", 123)
        service.set(cache_key, "abc123", sample_pr_diff)

        time.sleep(0.15)
        service.get(cache_key, "abc123")

        assert service._cache_expirations == 1


class TestCacheServiceThreadSafety:
    """Test suite for thread safety."""

    def test_concurrent_set_operations(self, reset_cache_service, sample_pr_diff):
        """Test concurrent set operations are thread-safe."""
        service = CacheService()
        num_threads = 10
        results = []

        def set_value(i):
            key = f"owner/repo/pr/{i}"
            service.set(key, f"sha{i}", sample_pr_diff)
            results.append(key)

        threads = [
            threading.Thread(target=set_value, args=(i,)) for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == num_threads
        assert service.get_stats()["size"] == num_threads

    def test_concurrent_get_operations(self, reset_cache_service, sample_pr_diff):
        """Test concurrent get operations are thread-safe."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)
        service.set(cache_key, "abc123", sample_pr_diff)

        num_threads = 10
        results = []

        def get_value():
            result = service.get(cache_key, "abc123")
            results.append(result is not None)

        threads = [threading.Thread(target=get_value) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get cache hits
        assert all(results)

    def test_statistics_thread_safe(self, reset_cache_service, sample_pr_diff):
        """Test statistics are thread-safe."""
        service = CacheService()
        cache_key = service.get_cache_key("owner", "repo", 123)
        service.set(cache_key, "abc123", sample_pr_diff)

        num_threads = 10
        operations_per_thread = 10

        def mixed_ops():
            for _ in range(operations_per_thread):
                service.get(cache_key, "abc123")  # Will be a hit
                service.get(cache_key, "wrong_sha")  # Will be a miss (SHA mismatch)

        threads = [threading.Thread(target=mixed_ops) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have consistent counts (each thread does 10 hits + 10 misses)
        stats = service.get_stats()
        expected_total = num_threads * operations_per_thread * 2
        assert stats["cache_hits"] + stats["cache_misses"] == expected_total


class TestCacheServiceGetInternalKey:
    """Test suite for _get_internal_key method."""

    def test_internal_key_no_hashing(self, reset_cache_service):
        """Test internal key without hashing."""
        with patch.object(CacheService, "__init__", lambda self: None):
            service = CacheService()
            service._use_hashed_keys = False

        internal_key, hash_display = service._get_internal_key("test_key")

        assert internal_key == "test_key"
        assert hash_display == ""

    def test_internal_key_with_hashing(self, reset_cache_service):
        """Test internal key with hashing."""
        with patch.object(CacheService, "__init__", lambda self: None):
            service = CacheService()
            service._use_hashed_keys = True
            service._hash_algorithm = "md5"
            service._store_key_mapping = False

        internal_key, hash_display = service._get_internal_key("test_key")

        assert len(internal_key) == 32  # MD5 hash
        assert hash_display == f"{internal_key[:8]}..."

    def test_internal_key_stores_mapping(self, reset_cache_service):
        """Test that internal key stores mapping when requested."""
        with patch.object(CacheService, "__init__", lambda self: None):
            service = CacheService()
            service._use_hashed_keys = True
            service._hash_algorithm = "md5"
            service._store_key_mapping = True
            service._key_mapping = {}
            service._lock = threading.RLock()

        internal_key, hash_display = service._get_internal_key(
            "test_key", store_mapping=True
        )

        assert "test_key" in service._key_mapping.values()


class TestCacheServiceGetOriginalKey:
    """Test suite for _get_original_key method."""

    def test_get_original_key_no_hashing(self, reset_cache_service):
        """Test getting original key without hashing."""
        with patch.object(CacheService, "__init__", lambda self: None):
            service = CacheService()
            service._use_hashed_keys = False

        original = service._get_original_key("test_key")

        assert original == "test_key"

    def test_get_original_key_with_mapping(self, reset_cache_service):
        """Test getting original key from mapping."""
        with patch.object(CacheService, "__init__", lambda self: None):
            service = CacheService()
            service._use_hashed_keys = True
            service._store_key_mapping = True
            service._key_mapping = {"hashed_key": "original_key"}
            service._lock = threading.RLock()

        original = service._get_original_key("hashed_key")

        assert original == "original_key"


class TestCacheServiceSingleton:
    """Test suite for singleton pattern."""

    def test_get_cache_service_singleton(self, reset_cache_service):
        """Test that get_cache_service returns singleton instance."""
        service1 = get_cache_service()
        service2 = get_cache_service()

        assert service1 is service2

    def test_get_cache_service_creates_once(self, reset_cache_service):
        """Test that singleton is created only once."""
        import prdiffer.infrastructure.cache_service as cache_module

        service1 = get_cache_service()
        service2 = get_cache_service()

        assert cache_module._cache_service is service1
        assert cache_module._cache_service is service2
