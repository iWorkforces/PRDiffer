"""Tests for CacheStore LRU storage with TTL eviction."""

import time

import pytest

from prdiffer.infrastructure.cache.store import CacheStore


@pytest.mark.unit
class TestCacheStoreInit:
    """Tests for CacheStore initialization."""

    def test_default_init(self):
        """Default init uses 1000 max_size and 600s TTL."""
        store = CacheStore()
        assert store.max_size == 1000
        assert store.ttl == 600
        assert store.size == 0

    def test_custom_init(self):
        """Custom max_size and TTL."""
        store = CacheStore(max_size=10, ttl=60)
        assert store.max_size == 10
        assert store.ttl == 60


@pytest.mark.unit
class TestCacheStoreGetSet:
    """Tests for get and set methods."""

    def test_set_and_get(self):
        """Basic set and get."""
        store = CacheStore()
        store.set("key1", {"data": "value1", "timestamp": time.time()})
        result = store.get("key1")
        assert result is not None
        assert result["data"] == "value1"

    def test_get_missing_key(self):
        """Get non-existent key returns None."""
        store = CacheStore()
        assert store.get("missing") is None

    def test_set_overwrites(self):
        """Set overwrites existing key."""
        store = CacheStore()
        store.set("key1", {"data": "old", "timestamp": time.time()})
        store.set("key1", {"data": "new", "timestamp": time.time()})
        result = store.get("key1")
        assert result["data"] == "new"

    def test_set_moves_to_end(self):
        """Set moves key to end of LRU order."""
        store = CacheStore(max_size=3)
        store.set("key1", {"data": "1", "timestamp": time.time()})
        store.set("key2", {"data": "2", "timestamp": time.time()})
        store.set("key3", {"data": "3", "timestamp": time.time()})

        keys = store.keys()
        assert keys == ["key1", "key2", "key3"]

    def test_get_moves_to_end(self):
        """Get moves accessed key to end (LRU behavior)."""
        store = CacheStore(max_size=5)
        store.set("key1", {"data": "1", "timestamp": time.time()})
        store.set("key2", {"data": "2", "timestamp": time.time()})
        store.set("key3", {"data": "3", "timestamp": time.time()})

        store.get("key1")  # Access key1, moves to end

        keys = store.keys()
        assert keys[-1] == "key1"


@pytest.mark.unit
class TestCacheStoreLRUEviction:
    """Tests for LRU eviction when cache is full."""

    def test_eviction_on_full(self):
        """Oldest entry is evicted when cache is full."""
        store = CacheStore(max_size=2)
        store.set("key1", {"data": "1", "timestamp": time.time()})
        store.set("key2", {"data": "2", "timestamp": time.time()})
        store.set("key3", {"data": "3", "timestamp": time.time()})

        assert store.size == 2
        assert store.get("key1") is None
        assert store.get("key2") is not None

    def test_eviction_preserves_most_recent(self):
        """Most recently accessed entries survive eviction."""
        store = CacheStore(max_size=2)
        store.set("key1", {"data": "1", "timestamp": time.time()})
        store.set("key2", {"data": "2", "timestamp": time.time()})

        store.get("key1")  # Access key1, making key2 the oldest

        store.set("key3", {"data": "3", "timestamp": time.time()})

        assert store.get("key2") is None
        assert store.get("key1") is not None


@pytest.mark.unit
class TestCacheStoreDelete:
    """Tests for delete method."""

    def test_delete_existing(self):
        """Delete existing key returns True."""
        store = CacheStore()
        store.set("key1", {"data": "1", "timestamp": time.time()})
        assert store.delete("key1") is True
        assert store.get("key1") is None
        assert store.size == 0

    def test_delete_missing(self):
        """Delete non-existent key returns False."""
        store = CacheStore()
        assert store.delete("missing") is False


@pytest.mark.unit
class TestCacheStoreClear:
    """Tests for clear method."""

    def test_clear_all(self):
        """Clear removes all entries."""
        store = CacheStore()
        store.set("key1", {"data": "1", "timestamp": time.time()})
        store.set("key2", {"data": "2", "timestamp": time.time()})
        store.clear()
        assert store.size == 0
        assert store.keys() == []


@pytest.mark.unit
class TestCacheStoreKeys:
    """Tests for keys method."""

    def test_keys_empty(self):
        """Empty store returns empty list."""
        store = CacheStore()
        assert store.keys() == []

    def test_keys_returns_all(self):
        """Keys returns all stored keys."""
        store = CacheStore()
        store.set("a", {"timestamp": time.time()})
        store.set("b", {"timestamp": time.time()})
        keys = store.keys()
        assert set(keys) == {"a", "b"}


@pytest.mark.unit
class TestCacheStoreTTL:
    """Tests for TTL expiration checking."""

    def test_not_expired(self):
        """Recent entry is not expired."""
        store = CacheStore(ttl=600)
        entry = {"timestamp": time.time()}
        assert store.is_expired(entry) is False

    def test_expired(self):
        """Old entry is expired."""
        store = CacheStore(ttl=1)
        entry = {"timestamp": time.time() - 2}
        assert store.is_expired(entry) is True

    def test_no_timestamp_not_expired(self):
        """Entry without timestamp is never expired."""
        store = CacheStore(ttl=1)
        entry = {"data": "value"}
        assert store.is_expired(entry) is False

    def test_evict_expired(self):
        """evict_expired removes stale entries."""
        store = CacheStore(ttl=1)
        store.set("old", {"data": "1", "timestamp": time.time() - 2})
        store.set("new", {"data": "2", "timestamp": time.time()})

        expired = store.evict_expired()

        assert "old" in expired
        assert store.size == 1
        assert store.get("new") is not None

    def test_evict_expired_empty(self):
        """evict_expired on empty store returns empty list."""
        store = CacheStore(ttl=600)
        expired = store.evict_expired()
        assert expired == []

    def test_evict_expired_none_expired(self):
        """evict_expired with no expired entries returns empty list."""
        store = CacheStore(ttl=600)
        store.set("key1", {"data": "1", "timestamp": time.time()})
        expired = store.evict_expired()
        assert expired == []


@pytest.mark.unit
class TestCacheStoreProperties:
    """Tests for properties."""

    def test_size_updates(self):
        """Size property reflects current count."""
        store = CacheStore()
        assert store.size == 0
        store.set("key1", {"timestamp": time.time()})
        assert store.size == 1
        store.set("key2", {"timestamp": time.time()})
        assert store.size == 2
        store.delete("key1")
        assert store.size == 1
