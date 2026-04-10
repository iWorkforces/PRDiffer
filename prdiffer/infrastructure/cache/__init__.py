"""Cache utilities for PR diff data.

This package provides caching for GitHub PR diff data with commit-based invalidation.

Modules:
- service: CacheService class for PR diff caching
- store: LRU cache storage with TTL and size-based eviction
- keys: Cache key generation and hashing utilities
"""
