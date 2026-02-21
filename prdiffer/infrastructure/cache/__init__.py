"""Cache utilities for PR diff data.

This package provides caching for GitHub PR diff data with commit-based invalidation.

Modules:
- service: CacheService class for PR diff caching
- store: LRU cache storage with TTL and size-based eviction
- keys: Cache key generation and hashing utilities
"""

from prdiffer.infrastructure.cache.service import (
    CacheService,
    get_cache_service,
)
from prdiffer.infrastructure.cache.store import CacheStore
from prdiffer.infrastructure.cache.keys import CacheKeyManager

__all__ = [
    'CacheService',
    'get_cache_service',
    'CacheStore',
    'CacheKeyManager',
]
