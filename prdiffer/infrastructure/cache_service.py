import hashlib
import time
import anyio
from collections import OrderedDict
from typing import Optional, Dict, Any, cast
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.services import CacheServiceInterface
from prdiffer.domain.exceptions import ValidationError
from prdiffer.domain.errors import E1010_INVALID_CONFIGURATION
from .logging.console_logger import get_logger


class CacheService(CacheServiceInterface):
    """Caching service for GitHub PR diff data with commit-based invalidation.

    This service provides caching for PR diff data using commit SHAs for cache invalidation.
    When a PR is updated (new commits pushed), the cache is automatically invalidated.
    """

    def __init__(self):
        """Initialize the cache service with empty cache and key hashing support.

        Loads configuration for cache key hashing:
        - cache.use_hashed_keys: Enable/disable hashing (default: True)
        - cache.hash_algorithm: Hash algorithm to use (default: md5)
        - cache.store_key_mapping: Store reverse mapping (default: True)
        - cache.ttl: Time-to-live for cache entries in seconds (default: 600)

        Thread Safety:
        - All cache operations are protected by a reentrant lock
        - Statistics counters are atomic within locked sections
        """
        # Async lock for cache operations
        self._lock = anyio.Lock()

        # LRU cache using OrderedDict for memory-efficient storage with eviction
        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.logger = get_logger()

        # Load cache hashing configuration
        from .settings import get_settings_service

        settings = get_settings_service()

        self._use_hashed_keys = settings.get("cache.use_hashed_keys", True)
        self._hash_algorithm = settings.get("cache.hash_algorithm", "md5")
        self._store_key_mapping = settings.get("cache.store_key_mapping", True)
        self._ttl = settings.get("cache.ttl", 600)  # Default 10 minutes
        self._cache_max_size = settings.get(
            "cache.max_size", 1000
        )  # Default 1000 entries

        # Reverse mapping: hashed_key -> original_key (for debugging and stats)
        self._key_mapping: dict[str, str] = {}

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_expirations = 0
        self._cache_evictions_ttl = 0  # Track TTL-based evictions
        self._cache_evictions_size = 0  # Track size-based evictions

        if self._use_hashed_keys:
            self.logger.info(
                f"Cache key hashing enabled (algorithm={self._hash_algorithm}, "
                f"mapping={self._store_key_mapping}, ttl={self._ttl}s)"
            )

    def get_cache_key(self, repo_owner: str, repo_name: str, pr_number: int) -> str:
        """Generate a cache key for the given repository and PR.

        Note: This returns the original (non-hashed) key format. Internal storage
        may use hashed keys based on configuration, but this method always returns
        the human-readable format for external use.

        Args:
            repo_owner: Repository owner/organization
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            str: Cache key in format "owner/repo/pr/number"
        """
        return f"{repo_owner}/{repo_name}/pr/{pr_number}"

    def _hash_key(self, key: str) -> str:
        """Hash cache key using configured algorithm.

        Args:
            key: Original cache key in format "owner/repo/pr/number"

        Returns:
            str: Hashed key (32 hex chars for MD5, 64 for SHA-256)

        Raises:
            ValueError: If unsupported hash algorithm is configured
        """
        if self._hash_algorithm == "md5":
            return hashlib.md5(key.encode("utf-8")).hexdigest()
        elif self._hash_algorithm == "sha256":
            return hashlib.sha256(key.encode("utf-8")).hexdigest()
        elif self._hash_algorithm == "sha256_short":
            return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        else:
            raise ValidationError(
                f"Unsupported hash algorithm: {self._hash_algorithm}",
                error_code=E1010_INVALID_CONFIGURATION,
            )

    async def _get_internal_key(
        self, original_key: str, store_mapping: bool = False
    ) -> tuple[str, str]:
        """Get internal key for cache operations with optional hashing.

        Thread-safe: Uses lock when modifying key_mapping.

        Args:
            original_key: Original cache key in format "owner/repo/pr/number"
            store_mapping: Whether to store reverse mapping (only True when setting)

        Returns:
            Tuple of (internal_key, hash_display):
                - internal_key: Key to use for cache storage (hashed if enabled)
                - hash_display: Short hash prefix for logging (empty if hashing disabled)
        """
        if not self._use_hashed_keys:
            return original_key, ""

        hashed = self._hash_key(original_key)

        # Store reverse mapping if configured and requested
        if store_mapping and self._store_key_mapping:
            async with self._lock:
                self._key_mapping[hashed] = original_key

        # Return hashed key and short display version
        return hashed, f"{hashed[:8]}..."

    async def _get_original_key(self, internal_key: str) -> str:
        """Get original key from internal key using reverse mapping.

        Thread-safe: Uses lock when reading key_mapping.

        Args:
            internal_key: The internal cache key (may be hashed)

        Returns:
            str: Original key if mapping exists, otherwise returns internal_key
        """
        if self._use_hashed_keys and self._store_key_mapping:
            async with self._lock:
                return self._key_mapping.get(internal_key, internal_key)
        return internal_key

    def _is_entry_expired(self, cached_data: dict[str, Any]) -> bool:
        """Check if a cache entry has expired based on TTL.

        Args:
            cached_data: The cached data dictionary containing timestamp

        Returns:
            bool: True if entry is expired, False otherwise
        """
        timestamp = cached_data.get("timestamp")
        if timestamp is None:
            return False  # No timestamp means no TTL check (backward compatibility)

        age = time.time() - float(timestamp)
        return bool(age > self._ttl)

    async def _evict_oldest_if_needed(self) -> None:
        """Evict oldest entries when cache exceeds max size (LRU eviction).

        This must be called while holding the lock. Also proactively removes
        expired entries to maintain cache hygiene.

        Thread Safety: Must be called with self._lock held.
        """
        current_time = time.time()

        # First, remove any expired entries (TTL-based eviction)
        expired_keys = []
        for key, entry in self.cache.items():
            age = current_time - float(entry["timestamp"])
            if age >= self._ttl:
                expired_keys.append(key)

        for key in expired_keys:
            self.cache.pop(key)
            self._key_mapping.pop(key, None)
            self._cache_evictions_ttl += 1

        if expired_keys:
            self.logger.debug(
                f"Cache eviction (TTL): removed {len(expired_keys)} expired entries "
                f"[size={len(self.cache)}/{self._cache_max_size}]"
            )

        # Then, remove oldest entries if still over size limit (LRU eviction)
        while len(self.cache) >= self._cache_max_size:
            # OrderedDict.popitem(last=False) removes oldest entry
            evicted_key, _ = self.cache.popitem(last=False)
            self._key_mapping.pop(evicted_key, None)
            self._cache_evictions_size += 1
            original_key = await self._get_original_key(evicted_key)
            self.logger.debug(
                f"Cache eviction (LRU): {original_key[:50]}... "
                f"[size={len(self.cache)}/{self._cache_max_size}]"
            )

    async def get(self, cache_key: str, current_commit_sha: str) -> Optional[PRDiff]:
        """Get cached PR diff data if it exists, commit SHA matches, and not expired.

        Thread-safe: All cache operations protected by lock.

        Args:
            cache_key: The cache key to look up (original format)
            current_commit_sha: The current head commit SHA from GitHub

        Returns:
            Optional[PRDiff]: Cached data if valid and not expired, None otherwise
        """
        internal_key, hash_display = await self._get_internal_key(cache_key)

        async with self._lock:
            if internal_key not in self.cache:
                self._cache_misses += 1
                self.logger.debug(
                    "Cache miss",
                    cache_key=cache_key,
                    hash=hash_display if self._use_hashed_keys else None,
                )
                return None

            cached_data = self.cache[internal_key]

            # Check TTL expiration first
            if self._is_entry_expired(cached_data):
                self._cache_expirations += 1
                self._cache_misses += 1
                # Remove expired entry
                del self.cache[internal_key]
                if self._use_hashed_keys and self._store_key_mapping:
                    self._key_mapping.pop(internal_key, None)
                self.logger.info(
                    "Cache entry expired (TTL)",
                    cache_key=cache_key,
                    hash=hash_display if self._use_hashed_keys else None,
                    ttl_seconds=self._ttl,
                )
                return None

            cached_commit_sha = cached_data.get("commit_sha")
            cached_result = cached_data.get("data")

            if cached_commit_sha == current_commit_sha and cached_result:
                self._cache_hits += 1
                # Mark as recently used by moving to end of OrderedDict
                self.cache.move_to_end(internal_key)
                self.logger.info(
                    "Cache hit",
                    cache_key=cache_key,
                    hash=hash_display if self._use_hashed_keys else None,
                    commit_sha=current_commit_sha,
                )
                # Cast to PRDiff since we know the type from set() method
                return cast(PRDiff, cached_result)
            else:
                self._cache_misses += 1
                self.logger.info(
                    "Cache miss (commit SHA mismatch)",
                    cache_key=cache_key,
                    hash=hash_display if self._use_hashed_keys else None,
                    cached_sha=cached_commit_sha,
                    current_sha=current_commit_sha,
                )
                return None

    async def set(self, cache_key: str, commit_sha: str, data: PRDiff) -> None:
        """Cache PR diff data with associated commit SHA.

        Thread-safe: All cache operations protected by lock.

        Args:
            cache_key: The cache key to store under (original format)
            commit_sha: The head commit SHA when this data was fetched
            data: The PRDiff data to cache
        """
        # Store mapping when setting data
        internal_key, hash_display = await self._get_internal_key(
            cache_key, store_mapping=True
        )

        async with self._lock:
            # If key exists, remove it first to update its position (move to end)
            if internal_key in self.cache:
                del self.cache[internal_key]
            else:
                # New entry - check if we need to evict
                await self._evict_oldest_if_needed()

            # Add entry at the end (most recently used)
            self.cache[internal_key] = {
                "commit_sha": commit_sha,
                "data": data,
                "timestamp": time.time(),
            }
        self.logger.info(
            "Cache set",
            cache_key=cache_key,
            hash=hash_display if self._use_hashed_keys else None,
            commit_sha=commit_sha,
        )

    async def invalidate(self, cache_key: str) -> None:
        """Invalidate cache for a specific PR.

        Thread-safe: All cache operations protected by lock.

        Args:
            cache_key: The cache key to invalidate (original format)
        """
        # Hash key without storing mapping (we're removing, not adding)
        if self._use_hashed_keys:
            internal_key = self._hash_key(cache_key)
            hash_display = f"{internal_key[:8]}..."
        else:
            internal_key = cache_key
            hash_display = ""

        async with self._lock:
            if internal_key in self.cache:
                del self.cache[internal_key]
                # Remove from reverse mapping too
                if self._use_hashed_keys and self._store_key_mapping:
                    self._key_mapping.pop(internal_key, None)
        self.logger.info(
            "Cache invalidated",
            cache_key=cache_key,
            hash=hash_display if self._use_hashed_keys else None,
        )

    async def clear(self) -> None:
        """Clear all cached data and key mappings.

        Thread-safe: All cache operations protected by lock.
        """
        async with self._lock:
            self.cache.clear()
            self._key_mapping.clear()
        self.logger.info("Cache cleared")

    def set_etag(self, cache_key: str, etag: str) -> None:
        """Cache ETag for a specific PR key.

        Args:
            cache_key: The cache key to store ETag under
            etag: The ETag value from HTTP response

        Store ETag for conditional requests.
        """
        cache_entry = self.cache.get(cache_key)
        if cache_entry is None:
            cache_entry = {
                "etag": etag,
                "timestamp": time.time(),
            }
            self.cache[cache_key] = cache_entry
        else:
            cache_entry["etag"] = etag
            cache_entry["timestamp"] = time.time()

    def get_etag(self, cache_key: str) -> Optional[str]:
        """Get stored ETag for a cache key."""
        cache_entry = self.cache.get(cache_key)
        if cache_entry is None:
            return None
        return cache_entry.get("etag")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        base_stats = {
            "cache_size": len(self.cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_expirations": self._cache_expirations,
            "cache_evictions_ttl": self._cache_evictions_ttl,
            "cache_evictions_size": self._cache_evictions_size,
        }

        if self._use_hashed_keys and self._store_key_mapping:
            base_stats["keys"] = list(self.cache.keys())

        return base_stats


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the global cache service instance (singleton pattern).

    Returns:
        CacheService: The global cache service instance
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
