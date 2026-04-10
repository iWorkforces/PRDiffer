"""Repository cache models and utilities.

BACKWARD COMPATIBILITY SHIM: This module has been flattened.
The canonical location is now ``prdiffer.infrastructure.cache.cache_repository``.
"""

from prdiffer.infrastructure.cache.cache_repository import (
    CacheEntry,
    with_lock,
)

__all__ = [
    "CacheEntry",
    "with_lock",
]
