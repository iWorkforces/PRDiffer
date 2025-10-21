"""Cache decorator utility for method-level caching with unhashable parameter support."""

import functools
import hashlib
import json
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional, Tuple, Set, Protocol, TypeVar, cast

# Type variable for generic function signatures
F = TypeVar("F", bound=Callable[..., Any])


class CacheableMethod(Protocol):
    """Protocol for methods that have been decorated with caching."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the cached method."""
        ...

    def clear_cache(self) -> None:
        """Clear the cache for this method."""
        ...


class CachingMixin:
    """Mixin class that provides caching capabilities to any class.

    This mixin provides a shared cache dictionary and cache management methods
    that can be used by the @cached_method decorator.
    """

    def __init__(self, max_cache_size: int = 1000, default_ttl: int = 300):
        """Initialize the caching mixin with size and TTL limits.

        Args:
            max_cache_size: Maximum number of cache entries (default: 1000)
            default_ttl: Default TTL in seconds (default: 300 = 5 minutes)
        """
        self._method_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_cache_size = max_cache_size
        self._default_ttl = default_ttl

    def _evict_expired_entries(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._method_cache.items()
            if current_time > entry.get("expires_at", float("inf"))
        ]
        for key in expired_keys:
            del self._method_cache[key]

    def _enforce_size_limit(self):
        """Enforce cache size limit using LRU eviction."""
        while len(self._method_cache) > self._max_cache_size:
            self._method_cache.popitem(last=False)  # Remove oldest entry

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
            "max_size": self._max_cache_size,
            "default_ttl": self._default_ttl,
        }


def _make_hashable(obj: Any, _seen: Optional[Set[int]] = None, _depth: int = 0) -> Any:
    """Convert an object to a hashable form recursively with circular reference protection.

    Args:
        obj: Object to convert
        _seen: Set of already processed object IDs (for circular reference detection)
        _depth: Current recursion depth (for depth protection)

    Returns:
        Hashable version of the object
    """
    MAX_DEPTH = 20
    if _depth > MAX_DEPTH:
        return f"<max_depth_exceeded:{type(obj).__name__}>"

    if _seen is None:
        _seen = set()

    # Primitives don't need circular reference checking
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    # Check for circular references using object id
    obj_id = id(obj)
    if obj_id in _seen:
        return f"<circular_ref:{type(obj).__name__}>"

    if isinstance(obj, (list, tuple)):
        _seen.add(obj_id)
        try:
            result = tuple(
                _make_hashable(item, _seen.copy(), _depth + 1) for item in obj
            )
        finally:
            _seen.discard(obj_id)
        return result
    elif isinstance(obj, dict):
        _seen.add(obj_id)
        try:
            result = tuple(
                sorted(
                    (k, _make_hashable(v, _seen.copy(), _depth + 1))
                    for k, v in obj.items()
                )
            )
        finally:
            _seen.discard(obj_id)
        return result
    elif isinstance(obj, set):
        _seen.add(obj_id)
        try:
            # Convert set items to hashable and sort them for consistent ordering
            hashable_items = [
                _make_hashable(item, _seen.copy(), _depth + 1) for item in obj
            ]
            # Sort with a fallback for unhashable types
            try:
                result = tuple(sorted(hashable_items))
            except TypeError:
                # If items can't be sorted, use string representation
                result = tuple(sorted(str(item) for item in hashable_items))
        finally:
            _seen.discard(obj_id)
        return result
    else:
        # For complex objects, use type and a simple representation to avoid exposing sensitive data
        return f"<{type(obj).__name__}:{id(type(obj))}>"


def _generate_cache_key(method_name: str, args: Tuple, kwargs: Dict) -> str:
    """Generate a cache key from method name and arguments.

    Args:
        method_name: Name of the method being cached
        args: Positional arguments (excluding self)
        kwargs: Keyword arguments

    Returns:
        String cache key
    """
    # Convert arguments to hashable forms with circular reference protection
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
        ttl: Time-to-live for cache entries in seconds
        key_prefix: Optional prefix for cache keys

    Returns:
        Decorated method with caching capability

    Example:
        class MyService(CachingMixin):
            @cached_method(ttl=60)
            def expensive_operation(self, param: List[str]) -> str:
                # Lists are automatically converted to tuples for caching
                return do_expensive_work(param)
    """

    def decorator(method: F) -> F:
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

            # Clean up expired entries periodically (every 10 cache operations)
            if (self._cache_hits + self._cache_misses) % 10 == 0:
                self._evict_expired_entries()

            # Check cache and validate TTL
            if cache_key in self._method_cache:
                entry = self._method_cache[cache_key]
                current_time = time.time()
                if current_time <= entry.get("expires_at", float("inf")):
                    # Move to end for LRU
                    self._method_cache.move_to_end(cache_key)
                    self._cache_hits += 1
                    return entry["value"]
                else:
                    # Entry expired, remove it
                    del self._method_cache[cache_key]

            # Cache miss - execute method
            self._cache_misses += 1
            result = method(self, *args, **kwargs)

            # Store in cache with TTL
            entry_ttl = ttl if ttl is not None else self._default_ttl
            expires_at = time.time() + entry_ttl if entry_ttl > 0 else float("inf")

            self._method_cache[cache_key] = {
                "value": result,
                "expires_at": expires_at,
                "created_at": time.time(),
            }

            # Enforce size limit
            self._enforce_size_limit()

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

        # Use setattr to dynamically add clear_cache method
        setattr(wrapper, "clear_cache", clear_method_cache)

        return cast(F, wrapper)

    return decorator


def conditional_cache(condition: Callable[[Any], bool], ttl: Optional[int] = None):
    """Decorator that caches based on a condition function.

    Args:
        condition: Function that takes the result and returns True if it should be cached
        ttl: Time-to-live for cache entries in seconds

    Returns:
        Decorated method with conditional caching

    Example:
        class MyService(CachingMixin):
            @conditional_cache(lambda result: result is not None, ttl=60)
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

            # Clean up expired entries periodically
            if (self._cache_hits + self._cache_misses) % 10 == 0:
                self._evict_expired_entries()

            # Check cache and validate TTL
            if cache_key in self._method_cache:
                entry = self._method_cache[cache_key]
                current_time = time.time()
                if current_time <= entry.get("expires_at", float("inf")):
                    self._method_cache.move_to_end(cache_key)
                    self._cache_hits += 1
                    return entry["value"]
                else:
                    del self._method_cache[cache_key]

            # Cache miss - execute method
            self._cache_misses += 1
            result = method(self, *args, **kwargs)

            # Store in cache only if condition is met
            if condition(result):
                entry_ttl = ttl if ttl is not None else self._default_ttl
                expires_at = time.time() + entry_ttl if entry_ttl > 0 else float("inf")

                self._method_cache[cache_key] = {
                    "value": result,
                    "expires_at": expires_at,
                    "created_at": time.time(),
                }

                # Enforce size limit
                self._enforce_size_limit()

            return result

        return wrapper

    return decorator
