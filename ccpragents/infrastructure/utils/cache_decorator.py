"""Cache decorator utility for method-level caching with unhashable parameter support."""

import functools
import hashlib
import json
from typing import Any, Callable, Dict, Optional, Tuple


class CachingMixin:
    """Mixin class that provides caching capabilities to any class.

    This mixin provides a shared cache dictionary and cache management methods
    that can be used by the @cached_method decorator.
    """

    def __init__(self):
        """Initialize the caching mixin with an empty cache."""
        self._method_cache: Dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def clear_cache(self):
        """Clear all cached method results."""
        self._method_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict containing cache size, hit rate, and other statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0

        return {
            "size": len(self._method_cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }


def _make_hashable(obj: Any) -> Any:
    """Convert an object to a hashable form recursively.

    Args:
        obj: Object to convert

    Returns:
        Hashable version of the object
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return tuple(_make_hashable(item) for item in obj)
    elif isinstance(obj, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
    elif isinstance(obj, set):
        return tuple(sorted(_make_hashable(item) for item in obj))
    else:
        # For complex objects, use their string representation
        return str(obj)


def _generate_cache_key(method_name: str, args: Tuple, kwargs: Dict) -> str:
    """Generate a cache key from method name and arguments.

    Args:
        method_name: Name of the method being cached
        args: Positional arguments (excluding self)
        kwargs: Keyword arguments

    Returns:
        String cache key
    """
    # Convert arguments to hashable forms
    hashable_args = _make_hashable(args)
    hashable_kwargs = _make_hashable(kwargs)

    # Create a dictionary representation for hashing
    key_data = {"method": method_name, "args": hashable_args, "kwargs": hashable_kwargs}

    # Generate a stable hash using JSON serialization
    key_json = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(key_json.encode()).hexdigest()

    return f"{method_name}_{key_hash}"


def cached_method(ttl: Optional[int] = None, key_prefix: Optional[str] = None):
    """Decorator for caching method results with support for unhashable parameters.

    This decorator can be applied to methods of classes that inherit from CachingMixin.
    It handles unhashable parameters by converting them to hashable forms.

    Args:
        ttl: Time-to-live for cache entries in seconds (not implemented yet)
        key_prefix: Optional prefix for cache keys

    Returns:
        Decorated method with caching capability

    Example:
        class MyService(CachingMixin):
            @cached_method()
            def expensive_operation(self, param: List[str]) -> str:
                # Lists are automatically converted to tuples for caching
                return do_expensive_work(param)
    """

    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            # Ensure the class has CachingMixin
            if not isinstance(self, CachingMixin):
                raise TypeError(
                    f"@cached_method can only be used on methods of classes "
                    f"that inherit from CachingMixin. {self.__class__.__name__} "
                    f"does not inherit from CachingMixin."
                )

            # Generate cache key
            method_name = method.__name__
            if key_prefix:
                method_name = f"{key_prefix}_{method_name}"

            cache_key = _generate_cache_key(method_name, args, kwargs)

            # Check cache
            if cache_key in self._method_cache:
                self._cache_hits += 1
                return self._method_cache[cache_key]

            # Cache miss - execute method
            self._cache_misses += 1
            result = method(self, *args, **kwargs)

            # Store in cache
            self._method_cache[cache_key] = result

            return result

        # Add a method to clear this specific method's cache
        def clear_method_cache(self):
            """Clear cache entries for this specific method."""
            method_name = method.__name__
            if key_prefix:
                method_name = f"{key_prefix}_{method_name}"

            keys_to_remove = [
                key
                for key in self._method_cache.keys()
                if key.startswith(f"{method_name}_")
            ]
            for key in keys_to_remove:
                del self._method_cache[key]

        wrapper.clear_cache = clear_method_cache

        return wrapper

    return decorator


def conditional_cache(condition: Callable[[Any], bool]):
    """Decorator that caches based on a condition function.

    Args:
        condition: Function that takes the result and returns True if it should be cached

    Returns:
        Decorated method with conditional caching

    Example:
        class MyService(CachingMixin):
            @conditional_cache(lambda result: result is not None)
            def maybe_expensive(self, param: str) -> Optional[str]:
                # Only cache non-None results
                return might_return_none(param)
    """

    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            # Ensure the class has CachingMixin
            if not isinstance(self, CachingMixin):
                raise TypeError(
                    "@conditional_cache can only be used on methods of classes "
                    "that inherit from CachingMixin."
                )

            # Generate cache key
            cache_key = _generate_cache_key(method.__name__, args, kwargs)

            # Check cache
            if cache_key in self._method_cache:
                self._cache_hits += 1
                return self._method_cache[cache_key]

            # Cache miss - execute method
            self._cache_misses += 1
            result = method(self, *args, **kwargs)

            # Store in cache only if condition is met
            if condition(result):
                self._method_cache[cache_key] = result

            return result

        return wrapper

    return decorator
