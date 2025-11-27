import hashlib
import time
from typing import Optional, Dict, Any, cast
from ccpragents.domain.entities.pr_diff import PRDiff
from ccpragents.domain.services import CacheServiceInterface
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
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger()

        # Load cache hashing configuration
        from .settings import get_settings_service

        settings = get_settings_service()

        self._use_hashed_keys = settings.get("cache.use_hashed_keys", True)
        self._hash_algorithm = settings.get("cache.hash_algorithm", "md5")
        self._store_key_mapping = settings.get("cache.store_key_mapping", True)
        self._ttl = settings.get("cache.ttl", 600)  # Default 10 minutes

        # Reverse mapping: hashed_key -> original_key (for debugging and stats)
        self._key_mapping: Dict[str, str] = {}

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_expirations = 0

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
            raise ValueError(f"Unsupported hash algorithm: {self._hash_algorithm}")

    def _get_internal_key(
        self, original_key: str, store_mapping: bool = False
    ) -> tuple[str, str]:
        """Get internal key for cache operations with optional hashing.

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
            self._key_mapping[hashed] = original_key

        # Return hashed key and short display version
        return hashed, f"{hashed[:8]}..."

    def _get_original_key(self, internal_key: str) -> str:
        """Get original key from internal key using reverse mapping.

        Args:
            internal_key: The internal cache key (may be hashed)

        Returns:
            str: Original key if mapping exists, otherwise returns internal_key
        """
        if self._use_hashed_keys and self._store_key_mapping:
            return self._key_mapping.get(internal_key, internal_key)
        return internal_key

    def _is_entry_expired(self, cached_data: Dict[str, Any]) -> bool:
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

    def get(self, cache_key: str, current_commit_sha: str) -> Optional[PRDiff]:
        """Get cached PR diff data if it exists, commit SHA matches, and not expired.

        Args:
            cache_key: The cache key to look up (original format)
            current_commit_sha: The current head commit SHA from GitHub

        Returns:
            Optional[PRDiff]: Cached data if valid and not expired, None otherwise
        """
        internal_key, hash_display = self._get_internal_key(cache_key)

        if internal_key not in self.cache:
            self._cache_misses += 1
            self.logger.debug(
                f"Cache miss [cache_key={cache_key}"
                + (f" hash={hash_display}" if hash_display else "")
                + "]"
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

    def set(self, cache_key: str, commit_sha: str, data: PRDiff) -> None:
        """Cache PR diff data with associated commit SHA.

        Args:
            cache_key: The cache key to store under (original format)
            commit_sha: The head commit SHA when this data was fetched
            data: The PRDiff data to cache
        """
        # Store mapping when setting data
        internal_key, hash_display = self._get_internal_key(
            cache_key, store_mapping=True
        )

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

    def invalidate(self, cache_key: str) -> None:
        """Invalidate cache for a specific PR.

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

    def clear(self) -> None:
        """Clear all cached data and key mappings."""
        self.cache.clear()
        self._key_mapping.clear()
        self.logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        When key hashing is enabled with mapping, returns original (human-readable) keys
        for better debuggability. Otherwise returns internal keys.

        Returns:
            Dict[str, Any]: Cache statistics including:
                - size: Number of cached entries
                - keys: List of cache keys (original format if mapping enabled)
                - total_entries: Total number of entries
                - hashing_enabled: Whether key hashing is active
                - mapping_size: Size of reverse mapping (if enabled)
                - ttl_seconds: TTL setting for cache entries
                - cache_hits: Number of cache hits
                - cache_misses: Number of cache misses
                - cache_expirations: Number of expired entries removed
                - hit_rate_percent: Cache hit rate percentage
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        base_stats = {
            "size": len(self.cache),
            "total_entries": len(self.cache),
            "ttl_seconds": self._ttl,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_expirations": self._cache_expirations,
            "hit_rate_percent": round(hit_rate, 2),
            "hashing_enabled": self._use_hashed_keys,
        }

        if self._use_hashed_keys and self._store_key_mapping:
            # Return original keys for better readability
            original_keys = [self._get_original_key(k) for k in self.cache.keys()]
            base_stats["keys"] = original_keys
            base_stats["mapping_size"] = len(self._key_mapping)
        else:
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
