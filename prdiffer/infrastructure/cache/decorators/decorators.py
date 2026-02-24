"""Cache decorators for method-level caching."""

import functools
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, TypeVar, cast

from prdiffer.infrastructure.cache.decorators.utils import _generate_cache_key

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class CachingMixin:
    """Mixin class that provides caching capabilities to any class.

    This mixin provides a shared cache dictionary and cache management methods
    that can be used by the @cached_method decorator.

    Thread Safety:
    - All cache operations are protected by a reentrant lock
    - Statistics counters are atomic within locked sections
    """

    def __init__(self, max_cache_size: int = 1000, default_ttl: int = 300) -> None:
        """Initialize the caching mixin with size and TTL limits.

        Args:
            max_cache_size: Maximum number of cache entries (default: 1000)
            default_ttl: Default TTL in seconds (default: 300 = 5 minutes)
        """
        self._cache_lock = threading.RLock()
        self._method_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_cache_size = max_cache_size
        self._default_ttl = default_ttl

    def _evict_expired_entries(self) -> None:
        """Remove expired cache entries.

        Thread-safe: Uses lock for all cache operations.
        """
        with self._cache_lock:
            current_time = time.time()
            expired_keys = [key for key, entry in self._method_cache.items() if current_time > entry.get("expires_at", float("inf"))]
            for key in expired_keys:
                del self._method_cache[key]

    def _enforce_size_limit(self) -> None:
        """Enforce cache size limit using LRU eviction.

        Thread-safe: Uses lock for all cache operations.
        """
        with self._cache_lock:
            while len(self._method_cache) > self._max_cache_size:
                self._method_cache.popitem(last=False)

    def clear_cache(self) -> None:
        """Clear all cached method results.

        Thread-safe: Uses lock for all cache operations.
        """
        with self._cache_lock:
            self._method_cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Thread-safe: Uses lock for all cache operations.

        Returns:
            Dict containing cache size, hit rate, and other statistics
        """
        with self._cache_lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / total_requests if total_requests else 0.0

            return {
                "size": len(self._method_cache),
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": hit_rate,
                "total_requests": total_requests,
                "max_size": self._max_cache_size,
                "default_ttl": self._default_ttl,
            }


def cached_method(ttl: int | None = None, key_prefix: str | None = None) -> Callable[[F], F]:
    """Decorator for caching method results with support for unhashable parameters.

    This decorator can be applied to methods of classes that inherit from CachingMixin.
    It handles unhashable parameters by converting them to hashable forms.

    Thread-safe: All cache operations protected by lock.

    Args:
        ttl: Time-to-live for cache entries in seconds
        key_prefix: Optional prefix for cache keys

    Returns:
        Decorated method with caching capability
    """

    def decorator(method: F) -> F:
        @functools.wraps(method)
        def wrapper(self: object, *args: Any, **kwargs: Any) -> Any:
            assert isinstance(self, CachingMixin), (
                f"@cached_method can only be used on methods of classes "
                f"that inherit from CachingMixin. {self.__class__.__name__} "
                f"does not inherit from CachingMixin."
            )

            method_name = method.__name__
            if key_prefix:
                method_name = f"{key_prefix}_{method_name}"

            cache_key = _generate_cache_key(method_name, args, kwargs)

            with self._cache_lock:
                if (self._cache_hits + self._cache_misses) % 10 == 0:
                    pass

                if cache_key in self._method_cache:
                    entry = self._method_cache[cache_key]
                    current_time = time.time()
                    if current_time <= entry.get("expires_at", float("inf")):
                        self._method_cache.move_to_end(cache_key)
                        self._cache_hits += 1
                        return entry["value"]
                    else:
                        del self._method_cache[cache_key]

            if (self._cache_hits + self._cache_misses) % 10 == 0:
                self._evict_expired_entries()

            with self._cache_lock:
                self._cache_misses += 1

            result = method(self, *args, **kwargs)

            entry_ttl = ttl if ttl is not None else self._default_ttl
            expires_at = time.time() + entry_ttl if entry_ttl > 0 else float("inf")

            with self._cache_lock:
                self._method_cache[cache_key] = {
                    "value": result,
                    "expires_at": expires_at,
                    "created_at": time.time(),
                }

            self._enforce_size_limit()

            return result

        def clear_method_cache(self: CachingMixin) -> None:
            """Clear cache entries for this specific method."""
            method_name = method.__name__
            if key_prefix:
                method_name = f"{key_prefix}_{method_name}"

            with self._cache_lock:
                keys_to_remove = [key for key in list(self._method_cache.keys()) if key.startswith(f"{method_name}_")]
                for key in keys_to_remove:
                    del self._method_cache[key]

        setattr(wrapper, "clear_cache", clear_method_cache)

        return cast(F, wrapper)

    return decorator
