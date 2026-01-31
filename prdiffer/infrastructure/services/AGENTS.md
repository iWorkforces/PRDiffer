# AGENTS.md - Infrastructure/Services

Infrastructure-level service implementations with retry, caching, fault tolerance.

## Guidelines

- Implement domain service interfaces
- Handle external API/service integrations
- **Add retry, circuit breaker, caching** to all external calls
- Log operations appropriately (sanitize sensitive data)
- **Use LazyLoggerMixin** to prevent circular imports

## Common Patterns

### Infrastructure Service with Retry + Circuit Breaker
```python
from prdiffer.domain.services import CacheServiceInterface
from prdiffer.infrastructure.utils.retry_handler import get_retry_handler
from prdiffer.infrastructure.logging.logger_factory import LazyLoggerMixin

class CacheService(CacheServiceInterface, LazyLoggerMixin):
    '''Cache service with retry logic and lazy logger'''
    
    def __init__(self, default_ttl: int = 300):
        self._cache: dict[str, Any] = {}
        self._ttl = default_ttl
        self._retry_handler = get_retry_handler()
    
    def get(self, key: str) -> Optional[Any]:
        self._logger.debug(f'Cache get: {key}')
        if key in self._cache:
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._logger.debug(f'Cache set: {key}')
        self._cache[key] = value
```

### PRDiffService (Orchestration)
```python
class PRDiffService:
    '''Orchestrates GitHub API + cache + retry for PR diff retrieval'''
    
    def __init__(
        self,
        github_service: GitHubAPIServiceInterface,
        cache_service: CacheServiceInterface,
        retry_handler: RetryHandlerInterface,
    ):
        self._github = github_service
        self._cache = cache_service
        self._retry = retry_handler
    
    async def get_pr_diff(self, pr_url: str) -> PRDiff:
        # 1. Check cache
        cached = self._cache.get(pr_url)
        if cached:
            return cached
        
        # 2. Fetch with retry
        diff = await self._retry.retry_async(
            lambda: self._github.get_pr_diff(pr_url)
        )
        
        # 3. Update cache
        self._cache.set(pr_url, diff)
        return diff
```

### Commit-Based Cache Invalidation
```python
import hashlib

class RepositoryCacheService:
    '''Commit-based cache with MD5 keys for precise invalidation'''
    
    def _generate_cache_key(self, commit_sha: str, file_path: str) -> str:
        '''MD5 hash of {commit_sha + file_path}'''
        key = f'{commit_sha}:{file_path}'
        return hashlib.md5(key.encode()).hexdigest()
    
    def get_file_content(self, commit_sha: str, file_path: str) -> Optional[str]:
        key = self._generate_cache_key(commit_sha, file_path)
        return self._cache.get(key)
```

## Anti-Patterns

- ❌ Missing retry wrapper for external API calls
- ❌ No circuit breaker integration
- ❌ Direct logging without LazyLoggerMixin (circular imports)
- ❌ Logging sensitive data (tokens, passwords)
- ❌ Cache without invalidation strategy

## Files

- `pr_diff_service.py`: PR diff infrastructure service (orchestration)
