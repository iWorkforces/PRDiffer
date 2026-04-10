"""Cache decorators for method-level caching.

BACKWARD COMPATIBILITY SHIM: This module has been flattened.
The canonical location is now ``prdiffer.infrastructure.cache.cache_decorators``.
"""

from prdiffer.infrastructure.cache.cache_decorators import (
    CachingMixin,
    cached_method,
    _generate_cache_key,
)

__all__ = [
    "CachingMixin",
    "cached_method",
    "_generate_cache_key",
]
