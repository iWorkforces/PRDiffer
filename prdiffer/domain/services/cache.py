from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from prdiffer.domain.entities.pr_diff import PRDiff


class CacheServiceInterface(ABC):
    """Abstract base class for caching services.

    This interface defines the contract for caching services that provide
    commit-based caching for PR diff data with automatic invalidation.
    """

    @abstractmethod
    def get_cache_key(self, repo_owner: str, repo_name: str, pr_number: int) -> str:
        """Generate a cache key for the given repository and PR.

        Args:
            repo_owner: Repository owner/organization
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            str: Cache key in format "owner/repo/pr/number"
        """
        pass

    @abstractmethod
    async def get(self, cache_key: str, current_commit_sha: str) -> Optional[PRDiff]:
        """Get cached PR diff data if it exists and commit SHA matches.

        Args:
            cache_key: The cache key to look up
            current_commit_sha: The current head commit SHA from GitHub

        Returns:
            Optional["PRDiff"]: Cached data if valid, None otherwise
        """
        pass

    @abstractmethod
    async def set(self, cache_key: str, commit_sha: str, data: PRDiff) -> None:
        """Cache PR diff data with associated commit SHA.

        Args:
            cache_key: The cache key to store under
            commit_sha: The head commit SHA when this data was fetched
            data: The PRDiff data to cache
        """
        pass

    @abstractmethod
    async def invalidate(self, cache_key: str) -> None:
        """Invalidate cache for a specific PR.

        Args:
            cache_key: The cache key to invalidate
        """
        pass

    @abstractmethod
    def get_etag(self, cache_key: str) -> Optional[str]:
        """Get stored ETag for a cache key."""
        pass

    @abstractmethod
    def set_etag(self, cache_key: str, etag: str) -> None:
        """Cache ETag for a specific PR key.

        Args:
            cache_key: The cache key to store ETag under
            etag: The ETag value from HTTP response

        Store ETag for conditional requests.
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict[str, Any]: Cache statistics including size and keys
        """
        pass
