import time
from typing import Optional, Dict, Any
from ccpragents.domain.entities.pr_diff import ExtraPRDiff
from ccpragents.domain.services import CacheServiceInterface
from .logging.console_logger import get_logger


class CacheService(CacheServiceInterface):
    '''Caching service for GitHub PR diff data with commit-based invalidation.

    This service provides caching for PR diff data using commit SHAs for cache invalidation.
    When a PR is updated (new commits pushed), the cache is automatically invalidated.
    '''

    def __init__(self):
        '''Initialize the cache service with empty cache and default TTL.'''
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger()

    def get_cache_key(self, repo_owner: str, repo_name: str, pr_number: int) -> str:
        '''Generate a cache key for the given repository and PR.

        Args:
            repo_owner: Repository owner/organization
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            str: Cache key in format "owner/repo/pr/number"
        '''
        return f"{repo_owner}/{repo_name}/pr/{pr_number}"

    def get(self, cache_key: str, current_commit_sha: str) -> Optional[ExtraPRDiff]:
        '''Get cached PR diff data if it exists and commit SHA matches.

        Args:
            cache_key: The cache key to look up
            current_commit_sha: The current head commit SHA from GitHub

        Returns:
            Optional[ExtraPRDiff]: Cached data if valid, None otherwise
        '''
        if cache_key not in self.cache:
            return None

        cached_data = self.cache[cache_key]
        cached_commit_sha = cached_data.get("commit_sha")
        cached_result = cached_data.get("data")

        if cached_commit_sha == current_commit_sha and cached_result:
            self.logger.info("Cache hit", cache_key=cache_key, commit_sha=current_commit_sha)
            return cached_result
        else:
            self.logger.info("Cache miss or invalid",
                           cache_key=cache_key,
                           cached_sha=cached_commit_sha,
                           current_sha=current_commit_sha)
            return None

    def set(self, cache_key: str, commit_sha: str, data: ExtraPRDiff) -> None:
        '''Cache PR diff data with associated commit SHA.

        Args:
            cache_key: The cache key to store under
            commit_sha: The head commit SHA when this data was fetched
            data: The ExtraPRDiff data to cache
        '''
        self.cache[cache_key] = {
            "commit_sha": commit_sha,
            "data": data,
            "timestamp": time.time()
        }
        self.logger.info("Cache set", cache_key=cache_key, commit_sha=commit_sha)

    def invalidate(self, cache_key: str) -> None:
        '''Invalidate cache for a specific PR.

        Args:
            cache_key: The cache key to invalidate
        '''
        if cache_key in self.cache:
            del self.cache[cache_key]
            self.logger.info("Cache invalidated", cache_key=cache_key)

    def clear(self) -> None:
        '''Clear all cached data.'''
        self.cache.clear()
        self.logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        '''Get cache statistics.

        Returns:
            Dict[str, Any]: Cache statistics including size and keys
        '''
        return {
            "size": len(self.cache),
            "keys": list(self.cache.keys()),
            "total_entries": sum(1 for _ in self.cache.values())
        }


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    '''Get the global cache service instance (singleton pattern).

    Returns:
        CacheService: The global cache service instance
    '''
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
