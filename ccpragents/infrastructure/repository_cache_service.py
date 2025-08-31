'''Repository caching service for GitHubPRDiffRepository instances.

This service provides caching of GitHub repository instances to avoid
repeated initialization of GitHub API objects for the same repositories.
'''
import time
from dataclasses import dataclass
from functools import wraps
from typing import Optional, Dict, Tuple, Callable
from threading import RLock
from ccpragents.domain.services import RepositoryCacheServiceInterface
from ccpragents.infrastructure import GitHubPRDiffRepository
from ccpragents.infrastructure.logging.console_logger import get_logger


@dataclass
class CacheEntry:
    '''Data class representing a cache entry.

    Attributes:
        repository: The cached GitHubPRDiffRepository instance
        timestamp: Unix timestamp when the entry was created/updated
        initialized: Whether the repository has been initialized
    '''
    repository: GitHubPRDiffRepository
    timestamp: float
    initialized: bool


def with_lock(lock_attr: str = "_lock"):
    '''Decorator for automatic lock management.

    Args:
        lock_attr: The attribute name of the RLock instance

    Returns:
        Decorated function that automatically acquires and releases the lock
    '''
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            lock = getattr(self, lock_attr)
            with lock:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator


class RepositoryCacheService(RepositoryCacheServiceInterface):
    '''Service for caching and reusing GitHubPRDiffRepository instances.

    This service maintains a cache of repository instances keyed by
    (repo_owner, repo_name, pr_number) to avoid repeated GitHub API
    initialization for the same repositories.
    '''

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        '''Initialize the repository cache service.

        Args:
            max_size: Maximum number of repository instances to cache
            ttl_seconds: Time-to-live for cached instances in seconds
        '''
        self._cache: Dict[Tuple[str, str, int], CacheEntry] = {}
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lock = RLock()
        self._logger = get_logger()

    def _get_cache_key(self, repo_owner: str, repo_name: str, pr_number: int) -> Tuple[str, str, int]:
        '''Generate a cache key from repository details.

        Args:
            repo_owner: Repository owner/organization
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            Tuple containing (repo_owner, repo_name, pr_number)
        '''
        return (repo_owner.lower(), repo_name.lower(), pr_number)

    @with_lock()
    def _clean_expired_entries(self):
        '''Remove expired entries from the cache.'''
        current_time = time.time()
        expired_keys = []

        for key, entry in self._cache.items():
            if current_time - entry.timestamp > self._ttl_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]
            self._logger.debug("Removed expired repository from cache",
                             repo_owner=key[0], repo_name=key[1], pr_number=key[2])

    @with_lock()
    def _evict_if_needed(self):
        '''Evict oldest entries if cache exceeds maximum size.'''
        if len(self._cache) <= self._max_size:
            return

        # Find oldest entries to remove without sorting (more efficient)
        # Convert to list to avoid "dictionary changed size during iteration" error
        entries_list = list(self._cache.items())
        # Sort by timestamp (oldest first) only the excess entries
        excess_count = len(entries_list) - self._max_size
        entries_to_remove = sorted(entries_list, key=lambda x: x[1].timestamp)[:excess_count]

        for key, _ in entries_to_remove:
            del self._cache[key]
            self._logger.debug("Evicted repository from cache due to size limit",
                             repo_owner=key[0], repo_name=key[1], pr_number=key[2])

    def _is_entry_valid(self, entry: CacheEntry, current_time: float) -> bool:
        '''Check if a cache entry is valid (not expired and initialized).

        Args:
            entry: The cache entry to validate
            current_time: Current timestamp for expiration check

        Returns:
            bool: True if the entry is valid, False otherwise
        '''
        # Check expiration
        if current_time - entry.timestamp > self._ttl_seconds:
            return False

        # Check if repository is initialized
        if not entry.initialized:
            return False

        return True

    def _get_valid_entry(self, cache_key: Tuple[str, str, int], extend_ttl: bool = False) -> Optional[CacheEntry]:
        '''Retrieve and validate a cache entry, removing it if invalid.

        Args:
            cache_key: The cache key to look up
            extend_ttl: Whether to extend the TTL on access

        Returns:
            CacheEntry if found and valid, None otherwise
        '''
        if cache_key not in self._cache:
            return None

        entry = self._cache[cache_key]
        current_time = time.time()

        # Check if entry is valid
        if not self._is_entry_valid(entry, current_time):
            del self._cache[cache_key]
            self._logger.debug("Repository cache entry invalid or expired",
                             repo_owner=cache_key[0], repo_name=cache_key[1], pr_number=cache_key[2])
            return None

        # Update timestamp to extend TTL if requested
        if extend_ttl:
            entry.timestamp = current_time

        return entry

    @with_lock()
    def insert(self, repository: GitHubPRDiffRepository) -> bool:
        '''Insert a repository instance into the cache.

        Args:
            repository: GitHubPRDiffRepository instance to cache

        Returns:
            bool: True if inserted successfully, False otherwise
        '''
        cache_key = self._get_cache_key(repository.repo_owner, repository.repo_name, repository.pr_number)

        self._clean_expired_entries()
        self._evict_if_needed()

        self._cache[cache_key] = CacheEntry(
            repository=repository,
            timestamp=time.time(),
            initialized=repository._initialized
        )

        self._logger.debug("Repository cached successfully",
                         repo_owner=repository.repo_owner,
                         repo_name=repository.repo_name,
                         pr_number=repository.pr_number)
        return True

    @with_lock()
    def retrieve(self, repo_owner: str, repo_name: str, pr_number: int) -> Optional[GitHubPRDiffRepository]:
        '''Retrieve a cached repository instance.

        Args:
            repo_owner: Repository owner/organization
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            GitHubPRDiffRepository instance if found and valid, None otherwise
        '''
        cache_key = self._get_cache_key(repo_owner, repo_name, pr_number)

        # Use the shared validation logic with TTL extension
        entry = self._get_valid_entry(cache_key, extend_ttl=True)
        if entry is None:
            # Log only if entry was not found (not if it was expired/invalid)
            if cache_key not in self._cache:
                self._logger.debug("Repository not found in cache",
                                 repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)
            return None

        self._logger.debug("Repository retrieved from cache",
                         repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)
        return entry.repository

    @with_lock()
    def validate(self, repo_owner: str, repo_name: str, pr_number: int) -> bool:
        '''Validate if a repository instance exists and is valid in the cache.

        Args:
            repo_owner: Repository owner/organization
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            bool: True if valid cached instance exists, False otherwise
        '''
        cache_key = self._get_cache_key(repo_owner, repo_name, pr_number)

        # Use the shared validation logic without TTL extension
        entry = self._get_valid_entry(cache_key, extend_ttl=False)
        return entry is not None

    @with_lock()
    def remove(self, repo_owner: str, repo_name: str, pr_number: int) -> bool:
        '''Remove a repository instance from the cache.

        Args:
            repo_owner: Repository owner/organization
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            bool: True if removed successfully, False if not found
        '''
        cache_key = self._get_cache_key(repo_owner, repo_name, pr_number)

        if cache_key in self._cache:
            del self._cache[cache_key]
            self._logger.debug("Repository removed from cache",
                             repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)
            return True
        return False

    @with_lock()
    def clear(self):
        '''Clear all entries from the cache.'''
        cache_size = len(self._cache)
        self._cache.clear()
        self._logger.info(f"Cleared repository cache ({cache_size} entries)")

    @with_lock()
    def size(self) -> int:
        '''Get the current number of entries in the cache.

        Returns:
            int: Number of cached repository instances
        '''
        return len(self._cache)

    @with_lock()
    def stats(self) -> Dict:
        '''Get cache statistics.

        Returns:
            Dict containing cache statistics
        '''
        current_time = time.time()
        initialized_count = 0
        expired_count = 0

        for entry in self._cache.values():
            if entry.initialized:
                initialized_count += 1
            if current_time - entry.timestamp > self._ttl_seconds:
                expired_count += 1

        return {
            'total_entries': len(self._cache),
            'initialized_entries': initialized_count,
            'expired_entries': expired_count,
            'max_size': self._max_size,
            'ttl_seconds': self._ttl_seconds
        }


# Singleton instance for global access
_repository_cache_service = None


def get_repository_cache_service() -> RepositoryCacheService:
    '''Get the singleton repository cache service instance.

    Returns:
        RepositoryCacheService singleton instance
    '''
    global _repository_cache_service
    if _repository_cache_service is None:
        _repository_cache_service = RepositoryCacheService()
    return _repository_cache_service
