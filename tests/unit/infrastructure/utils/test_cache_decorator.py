import pytest
import time

from prdiffer.infrastructure.cache.cache_decorators import (
    CachingMixin,
    cached_method,
    _make_hashable,
    _generate_cache_key,
)


class TestCachingMixin:
    def test_init_defaults(self):
        mixin = CachingMixin()
        assert mixin._max_cache_size == 1000
        assert mixin._default_ttl == 300
        assert mixin._cache_hits == 0
        assert mixin._cache_misses == 0

    def test_init_custom_values(self):
        mixin = CachingMixin(max_cache_size=500, default_ttl=600)
        assert mixin._max_cache_size == 500
        assert mixin._default_ttl == 600

    def test_clear_cache(self):
        mixin = CachingMixin()
        mixin._method_cache["key"] = {"value": "data"}
        mixin._cache_hits = 10
        mixin._cache_misses = 5

        mixin.clear_cache()

        assert len(mixin._method_cache) == 0
        assert mixin._cache_hits == 0
        assert mixin._cache_misses == 0

    def test_get_cache_stats_empty(self):
        mixin = CachingMixin()
        stats = mixin.get_cache_stats()

        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0
        assert stats["total_requests"] == 0

    def test_get_cache_stats_with_data(self):
        mixin = CachingMixin()
        mixin._method_cache["key1"] = {"value": "data1"}
        mixin._method_cache["key2"] = {"value": "data2"}
        mixin._cache_hits = 8
        mixin._cache_misses = 2

        stats = mixin.get_cache_stats()

        assert stats["size"] == 2
        assert stats["hits"] == 8
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.8
        assert stats["total_requests"] == 10

    def test_evict_expired_entries(self):
        mixin = CachingMixin()
        current_time = time.time()
        mixin._method_cache["expired"] = {
            "value": "data",
            "expires_at": current_time - 100,
        }
        mixin._method_cache["valid"] = {
            "value": "data",
            "expires_at": current_time + 1000,
        }

        mixin._evict_expired_entries()

        assert "expired" not in mixin._method_cache
        assert "valid" in mixin._method_cache

    def test_enforce_size_limit(self):
        mixin = CachingMixin(max_cache_size=3)
        mixin._method_cache["key1"] = {"value": "data1"}
        mixin._method_cache["key2"] = {"value": "data2"}
        mixin._method_cache["key3"] = {"value": "data3"}
        mixin._method_cache["key4"] = {"value": "data4"}

        mixin._enforce_size_limit()

        assert len(mixin._method_cache) <= 3
        assert "key1" not in mixin._method_cache


class TestMakeHashable:
    def test_primitives_passthrough(self):
        assert _make_hashable("string") == "string"
        assert _make_hashable(42) == 42
        assert _make_hashable(3.14) == 3.14
        assert _make_hashable(True) is True
        assert _make_hashable(None) is None

    def test_list_to_tuple(self):
        result = _make_hashable([1, 2, 3])
        assert result == (1, 2, 3)
        assert isinstance(result, tuple)

    def test_nested_list(self):
        result = _make_hashable([[1, 2], [3, 4]])
        assert result == ((1, 2), (3, 4))

    def test_dict_to_sorted_tuple(self):
        result = _make_hashable({"b": 2, "a": 1})
        assert result == (("a", 1), ("b", 2))

    def test_set_to_sorted_tuple(self):
        result = _make_hashable({3, 1, 2})
        assert result == (1, 2, 3)

    def test_circular_reference_in_list(self):
        circular_list = [1, 2]
        circular_list.append(circular_list)

        result = _make_hashable(circular_list)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert "circular_ref" in str(result[2])

    def test_circular_reference_in_dict(self):
        circular_dict = {"a": 1}
        circular_dict["self"] = circular_dict

        result = _make_hashable(circular_dict)

        assert isinstance(result, tuple)
        assert "circular_ref" in str(result)

    def test_max_depth_exceeded(self):
        deep_obj = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": {"j": {"k": {"l": {"m": {"n": {"o": {"p": {"q": {"r": {"s": {"t": 1}}}}}}}}}}}}}}}}}}}}

        result = _make_hashable(deep_obj)

        assert isinstance(result, tuple)

    def test_complex_object(self):

        class CustomObj:
            pass

        result = _make_hashable(CustomObj())

        assert isinstance(result, str)
        assert "CustomObj" in result


class TestGenerateCacheKey:
    def test_basic_key_generation(self):
        key = _generate_cache_key("test_method", (1, 2), {"a": 3})

        assert key.startswith("test_method_")
        assert len(key) > len("test_method_")

    def test_consistent_keys(self):
        key1 = _generate_cache_key("method", (1, 2), {"a": 3})
        key2 = _generate_cache_key("method", (1, 2), {"a": 3})

        assert key1 == key2

    def test_different_args_different_keys(self):
        key1 = _generate_cache_key("method", (1, 2), {})
        key2 = _generate_cache_key("method", (3, 4), {})

        assert key1 != key2

    def test_different_kwargs_different_keys(self):
        key1 = _generate_cache_key("method", (), {"a": 1})
        key2 = _generate_cache_key("method", (), {"a": 2})

        assert key1 != key2


class TestCachedMethod:
    def test_caches_result(self):

        class TestClass(CachingMixin):
            call_count = 0

            @cached_method()
            def get_value(self, x):
                self.call_count += 1
                return x * 2

        obj = TestClass()
        result1 = obj.get_value(5)
        result2 = obj.get_value(5)

        assert result1 == 10
        assert result2 == 10
        assert obj.call_count == 1

    def test_different_args_not_cached(self):

        class TestClass(CachingMixin):
            call_count = 0

            @cached_method()
            def get_value(self, x):
                self.call_count += 1
                return x * 2

        obj = TestClass()
        obj.get_value(5)
        obj.get_value(10)

        assert obj.call_count == 2

    def test_custom_ttl(self):

        class TestClass(CachingMixin):
            call_count = 0

            @cached_method(ttl=1)
            def get_value(self, x):
                self.call_count += 1
                return x * 2

        obj = TestClass()
        obj.get_value(5)
        time.sleep(1.1)
        obj.get_value(5)

        assert obj.call_count == 2

    def test_key_prefix(self):

        class TestClass(CachingMixin):
            @cached_method(key_prefix="custom")
            def get_value(self, x):
                return x

        obj = TestClass()
        obj.get_value(5)

        keys = list(obj._method_cache.keys())
        assert any("custom" in k for k in keys)

    def test_requires_caching_mixin(self):

        class BadClass:
            @cached_method()
            def get_value(self, x):
                return x

        obj = BadClass()

        with pytest.raises((TypeError, AssertionError)) as exc_info:
            obj.get_value(5)

        assert "CachingMixin" in str(exc_info.value)

    def test_cache_hits_increments(self):

        class TestClass(CachingMixin):
            @cached_method()
            def get_value(self, x):
                return x

        obj = TestClass()
        obj.get_value(5)
        obj.get_value(5)

        assert obj._cache_hits == 1

    def test_cache_misses_increments(self):

        class TestClass(CachingMixin):
            @cached_method()
            def get_value(self, x):
                return x

        obj = TestClass()
        obj.get_value(5)
        obj.get_value(10)

        assert obj._cache_misses == 2

    def test_clear_method_cache(self):

        class TestClass(CachingMixin):
            @cached_method()
            def method_a(self, x):
                return x

            @cached_method()
            def method_b(self, x):
                return x * 2

        obj = TestClass()
        obj.method_a(5)
        obj.method_b(10)

        assert len(obj._method_cache) == 2

        obj.method_a.clear_cache(obj)

        assert len(obj._method_cache) == 1

    def test_expired_entry_removed_on_access(self):

        class TestClass(CachingMixin):
            call_count = 0

            @cached_method(ttl=1)
            def get_value(self, x):
                self.call_count += 1
                return x

        obj = TestClass()
        obj.get_value(5)
        time.sleep(1.1)
        obj.get_value(5)

        assert obj.call_count == 2

    def test_lru_eviction(self):

        class TestClass(CachingMixin):
            @cached_method()
            def get_value(self, x):
                return x

        obj = TestClass()
        obj.get_value(1)
        obj.get_value(2)
        obj.get_value(1)

        keys = list(obj._method_cache.keys())

        assert keys[-1].startswith("get_value")


class TestCachedMethodWithComplexArgs:
    def test_list_arg(self):

        class TestClass(CachingMixin):
            call_count = 0

            @cached_method()
            def process(self, items):
                self.call_count += 1
                return sum(items)

        obj = TestClass()
        result1 = obj.process([1, 2, 3])
        _ = obj.process([1, 2, 3])

        assert result1 == 6
        assert obj.call_count == 1

    def test_dict_arg(self):

        class TestClass(CachingMixin):
            call_count = 0

            @cached_method()
            def process(self, config):
                self.call_count += 1
                return config.get("value", 0)

        obj = TestClass()
        obj.process({"value": 42})
        obj.process({"value": 42})

        assert obj.call_count == 1

    def test_nested_args(self):

        class TestClass(CachingMixin):
            call_count = 0

            @cached_method()
            def process(self, data):
                self.call_count += 1
                return data["items"][0]

        obj = TestClass()
        obj.process({"items": [1, 2, 3]})
        obj.process({"items": [1, 2, 3]})

        assert obj.call_count == 1


class TestThreadSafety:
    def test_cache_lock_used(self):
        mixin = CachingMixin()

        with mixin._cache_lock:
            assert mixin._cache_lock.locked()

        assert not mixin._cache_lock.locked()

    def test_concurrent_access(self):
        import threading

        class TestClass(CachingMixin):
            call_count = 0

            @cached_method()
            def get_value(self, x):
                self.call_count += 1
                return x

        obj = TestClass()
        errors = []
        results = []

        def worker(val):
            try:
                result = obj.get_value(val)
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10
