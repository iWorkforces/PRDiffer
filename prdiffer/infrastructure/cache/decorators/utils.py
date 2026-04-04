"""Utility functions for cache key generation."""

import hashlib
import json
import logging
from typing import Any, cast

logger = logging.getLogger(__name__)

__all__ = ["_make_hashable", "_generate_cache_key"]


def _make_hashable(obj: Any, _seen: set[int] | None = None, _depth: int = 0) -> Any:
    """Convert an object to a hashable form recursively with circular reference protection."""
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
            seq = cast("list[Any] | tuple[Any, ...]", obj)
            result: tuple[Any, ...] = tuple(_make_hashable(item, _seen.copy(), _depth + 1) for item in seq)
        finally:
            _seen.discard(obj_id)
        return result
    elif isinstance(obj, dict):
        _seen.add(obj_id)
        try:
            d = cast("dict[Any, Any]", obj)
            pairs: list[tuple[Any, Any]] = [(k, _make_hashable(v, _seen.copy(), _depth + 1)) for k, v in d.items()]
            result = tuple(sorted(pairs))
        finally:
            _seen.discard(obj_id)
        return result
    elif isinstance(obj, set):
        _seen.add(obj_id)
        try:
            s = cast("set[Any]", obj)
            hashable_items: list[Any] = [_make_hashable(item, _seen.copy(), _depth + 1) for item in s]
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
        obj_as_object: object = obj
        obj_type = type(obj_as_object)
        return f"<{obj_type.__name__}:{id(obj_type)}>"


def _generate_cache_key(method_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Generate a cache key from method name and arguments."""
    hashable_args = _make_hashable(args)
    hashable_kwargs = _make_hashable(kwargs)

    key_data: dict[str, Any] = {"method": method_name, "args": hashable_args, "kwargs": hashable_kwargs}

    key_json = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(key_json.encode()).hexdigest()

    return f"{method_name}_{key_hash}"
