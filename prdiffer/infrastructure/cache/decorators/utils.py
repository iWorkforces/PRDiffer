"""Utility functions for cache key generation."""

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _make_hashable(obj: Any, _seen: set[int] | None = None, _depth: int = 0) -> Any:
    """Convert an object to a hashable form recursively with circular reference protection.

    Args:
        obj: Object to convert
        _seen: Set of already processed object IDs
        _depth: Current recursion depth

    Returns:
        Hashable version of the object
    """
    MAX_DEPTH = 20
    if _depth > MAX_DEPTH:
        return f"<max_depth_exceeded:{type(obj).__name__}>"

    if _seen is None:
        _seen = set()

    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    obj_id = id(obj)
    if obj_id in _seen:
        return f"<circular_ref:{type(obj).__name__}>"

    if isinstance(obj, (list, tuple)):
        _seen.add(obj_id)
        try:
            result = tuple(_make_hashable(item, _seen.copy(), _depth + 1) for item in obj)
        finally:
            _seen.discard(obj_id)
        return result
    elif isinstance(obj, dict):
        _seen.add(obj_id)
        try:
            result = tuple(sorted((k, _make_hashable(v, _seen.copy(), _depth + 1)) for k, v in obj.items()))
        finally:
            _seen.discard(obj_id)
        return result
    elif isinstance(obj, set):
        _seen.add(obj_id)
        try:
            hashable_items = [_make_hashable(item, _seen.copy(), _depth + 1) for item in obj]
            try:
                result = tuple(sorted(hashable_items))
            except TypeError as e:
                logger.debug(
                    "Cannot sort hashable items, using string representation",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "item_count": len(hashable_items),
                    },
                )
                result = tuple(sorted(str(item) for item in hashable_items))
        finally:
            _seen.discard(obj_id)
        return result
    else:
        return f"<{type(obj).__name__}:{id(type(obj))}>"


def _generate_cache_key(method_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a cache key from method name and arguments.

    Args:
        method_name: Name of the method being cached
        args: Positional arguments (excluding self)
        kwargs: Keyword arguments

    Returns:
        String cache key
    """
    hashable_args = _make_hashable(args)
    hashable_kwargs = _make_hashable(kwargs)

    key_data = {"method": method_name, "args": hashable_args, "kwargs": hashable_kwargs}

    key_json = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(key_json.encode()).hexdigest()

    return f"{method_name}_{key_hash}"
