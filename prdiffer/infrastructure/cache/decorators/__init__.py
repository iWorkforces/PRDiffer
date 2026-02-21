"""Cache decorators for method-level caching with unhashable parameter support.

This module provides caching decorators and utilities.
"""

from prdiffer.infrastructure.cache.decorators.decorators import (
    CachingMixin,
    cached_method,
)
from prdiffer.infrastructure.cache.decorators.utils import (
    _make_hashable,
    _generate_cache_key,
)

__all__ = [
    "CachingMixin",
    "cached_method",
    "_make_hashable",
    "_generate_cache_key",
]
