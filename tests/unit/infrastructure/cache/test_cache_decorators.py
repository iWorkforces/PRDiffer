"""Tests for cache decorators: _make_hashable, _generate_cache_key, CachingMixin, @cached_method."""

import time
from unittest.mock import patch

import pytest

from prdiffer.infrastructure.cache.cache_decorators import (
    CachingMixin,
    _generate_cache_key,
    _make_hashable,
    cached_method,
)


# ---------------------------------------------------------------------------
# _make_hashable
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMakeHashable:
    """Test _make_hashable converts unhashable types to hashable forms."""

    def test_primitives_unchanged(self):
        assert _make_hashable("hello") == "hello"
        assert _make_hashable(42) == 42
        assert _make_hashable(3.14) == 3.14
        assert _make_hashable(True) is True
        assert _make_hashable(None) is None

    def test_list_becomes_tuple(self):
        result = _make_hashable([1, 2, 3])
        assert result == (1, 2, 3)
        assert isinstance(result, tuple)

    def test_nested_list(self):
        result = _make_hashable([[1, 2], [3, 4]])
        assert result == ((1, 2), (3, 4))

    def test_dict_becomes_sorted_tuple_of_pairs(self):
        result = _make_hashable({"b": 2, "a": 1})
        assert result == (("a", 1), ("b", 2))

    def test_set_becomes_sorted_tuple(self):
        result = _make_hashable({3, 1, 2})
        assert result == (1, 2, 3)

    def test_tuple_passthrough(self):
        result = _make_hashable((1, 2, 3))
        assert result == (1, 2, 3)

    def test_custom_object_returns_string_repr(self):
        class Foo:
            pass

        result = _make_hashable(Foo())
        assert result.startswith("<Foo:")

    def test_max_depth_protection(self):
        deep = [1]
        current = deep
        for _ in range(25):
            nested: list[object] = [current]
            current = nested
        result = _make_hashable(current)
        assert isinstance(result, tuple)

    def test_circular_reference(self):
        a: list[object] = []
        a.append(a)
        result = _make_hashable(a)
        assert isinstance(result, tuple)


# ---------------------------------------------------------------------------
# _generate_cache_key
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateCacheKey:
    """Test cache key generation."""

    def test_returns_string_with_method_prefix(self):
        key = _generate_cache_key("my_method", (1, 2), {"k": "v"})
        assert key.startswith("my_method_")

    def test_same_inputs_same_key(self):
        k1 = _generate_cache_key("m", (1,), {"x": 1})
        k2 = _generate_cache_key("m", (1,), {"x": 1})
        assert k1 == k2

    def test_different_args_different_key(self):
        k1 = _generate_cache_key("m", (1,), {})
        k2 = _generate_cache_key("m", (2,), {})
        assert k1 != k2

    def test_different_kwargs_different_key(self):
        k1 = _generate_cache_key("m", (), {"a": 1})
        k2 = _generate_cache_key("m", (), {"a": 2})
        assert k1 != k2

    def test_different_method_different_key(self):
        k1 = _generate_cache_key("foo", (1,), {})
        k2 = _generate_cache_key("bar", (1,), {})
        assert k1 != k2

    def test_unhashable_args_still_work(self):
        key = _generate_cache_key("m", ([1, 2], {"a": "b"}), {})
        assert isinstance(key, str)
        assert key.startswith("m_")


# ---------------------------------------------------------------------------
# CachingMixin
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCachingMixin:
    """Test CachingMixin base class."""

    def test_init_defaults(self):
        mixin = CachingMixin()
        assert mixin._max_cache_size == 1000
        assert mixin._default_ttl == 300
        assert mixin._cache_hits == 0
        assert mixin._cache_misses == 0

    def test_init_custom_params(self):
        mixin = CachingMixin(max_cache_size=50, default_ttl=60)
        assert mixin._max_cache_size == 50
        assert mixin._default_ttl == 60

    def test_get_cache_stats_empty(self):
        mixin = CachingMixin()
        stats = mixin.get_cache_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["total_requests"] == 0

    def test_clear_cache(self):
        mixin = CachingMixin()
        mixin._method_cache["key"] = {"value": 42, "expires_at": float("inf")}
        mixin._cache_hits = 5
        mixin._cache_misses = 3
        mixin.clear_cache()
        assert len(mixin._method_cache) == 0
        assert mixin._cache_hits == 0
        assert mixin._cache_misses == 0

    def test_evict_expired_entries(self):
        mixin = CachingMixin()
        mixin._method_cache["expired"] = {"value": 1, "expires_at": time.time() - 10}
        mixin._method_cache["valid"] = {"value": 2, "expires_at": time.time() + 1000}
        mixin._evict_expired_entries()
        assert "expired" not in mixin._method_cache
        assert "valid" in mixin._method_cache

    def test_enforce_size_limit(self):
        mixin = CachingMixin(max_cache_size=2)
        mixin._method_cache["a"] = {"value": 1}
        mixin._method_cache["b"] = {"value": 2}
        mixin._method_cache["c"] = {"value": 3}
        mixin._enforce_size_limit()
        assert len(mixin._method_cache) <= 2
        # LRU: first inserted ('a') should be evicted
        assert "c" in mixin._method_cache


# ---------------------------------------------------------------------------
# @cached_method decorator
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCachedMethod:
    """Test @cached_method decorator."""

    def test_basic_caching(self):
        class MyService(CachingMixin):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            @cached_method()
            def compute(self, x: int) -> int:
                self.call_count += 1
                return x * 2

        svc = MyService()
        assert svc.compute(5) == 10
        assert svc.compute(5) == 10  # cached
        assert svc.call_count == 1  # only called once

    def test_different_args_not_cached(self):
        class MyService(CachingMixin):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            @cached_method()
            def compute(self, x: int) -> int:
                self.call_count += 1
                return x * 2

        svc = MyService()
        svc.compute(1)
        svc.compute(2)
        assert svc.call_count == 2

    def test_cache_stats_updated(self):
        class MyService(CachingMixin):
            def __init__(self):
                super().__init__()

            @cached_method()
            def compute(self, x: int) -> int:
                return x

        svc = MyService()
        svc.compute(1)  # miss
        svc.compute(1)  # hit
        svc.compute(2)  # miss
        stats = svc.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2

    def test_ttl_expiry(self):
        class MyService(CachingMixin):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            @cached_method(ttl=1)
            def compute(self, x: int) -> int:
                self.call_count += 1
                return x

        svc = MyService()
        svc.compute(1)

        # Patch time to simulate TTL expiry
        with patch("prdiffer.infrastructure.cache.cache_decorators.time") as mock_time:
            mock_time.time.return_value = time.time() + 100
            svc.compute(1)  # should be a miss now

        assert svc.call_count == 2

    def test_key_prefix(self):
        class MyService(CachingMixin):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            @cached_method(key_prefix="custom")
            def compute(self, x: int) -> int:
                self.call_count += 1
                return x

        svc = MyService()
        svc.compute(1)
        # Check the cache key has the prefix
        keys = list(svc._method_cache.keys())
        assert len(keys) == 1
        assert keys[0].startswith("custom_compute_")

    def test_assert_requires_caching_mixin(self):
        class BadService:
            @cached_method()
            def compute(self) -> int:
                return 42

        svc = BadService()
        with pytest.raises(AssertionError, match="CachingMixin"):
            svc.compute()

    def test_clear_method_cache(self):
        class MyService(CachingMixin):
            def __init__(self):
                super().__init__()

            @cached_method()
            def compute(self, x: int) -> int:
                return x

        svc = MyService()
        svc.compute(1)
        svc.compute(2)
        assert svc.get_cache_stats()["size"] == 2

        # clear_cache for the specific method
        svc.compute.clear_cache(svc)
        assert svc.get_cache_stats()["size"] == 0

    def test_unhashable_args(self):
        class MyService(CachingMixin):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            @cached_method()
            def compute(self, data: list[int]) -> int:
                self.call_count += 1
                return sum(data)

        svc = MyService()
        assert svc.compute([1, 2, 3]) == 6
        assert svc.compute([1, 2, 3]) == 6  # cached
        assert svc.call_count == 1

    def test_size_limit_eviction(self):
        class MyService(CachingMixin):
            def __init__(self):
                super().__init__(max_cache_size=3)

            @cached_method()
            def compute(self, x: int) -> int:
                return x

        svc = MyService()
        for i in range(5):
            svc.compute(i)
        assert svc.get_cache_stats()["size"] <= 3
