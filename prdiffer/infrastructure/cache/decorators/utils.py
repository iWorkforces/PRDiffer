"""Utility functions for cache key generation.

BACKWARD COMPATIBILITY SHIM: This module has been flattened.
The canonical location is now ``prdiffer.infrastructure.cache.cache_decorators``.
"""

from prdiffer.infrastructure.cache.cache_decorators import (
    _make_hashable,
    _generate_cache_key,
)

__all__ = ["_make_hashable", "_generate_cache_key"]
