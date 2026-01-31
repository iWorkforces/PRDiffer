# AGENTS.md - Infrastructure/GitHub

GitHub API client with retry, circuit breaker, ETag support.

## Guidelines

- Use PyGithub library for API calls
- **Always wrap with UnifiedRetryHandler** (retry logic)
- **Always integrate CircuitBreaker** (fault tolerance)
- Cache file contents with commit-based invalidation
- **Handle rate limiting** (403/429 with smart retry)
- **ETag support** for bandwidth reduction (304 responses)

## Common Patterns

### API Client with Retry + Circuit Breaker
```python
from github import Github
from github.Auth import Token
from prdiffer.domain.services import GitHubAPIServiceInterface
from prdiffer.infrastructure.utils.retry_handler import get_retry_handler
from prdiffer.infrastructure.utils.circuit_breaker import get_circuit_breaker

class GitHubAPIClient(GitHubAPIServiceInterface):
    '''PyGithub wrapper with retry + circuit breaker integration'''
    
    def __init__(
        self,
        max_retries: int = 3,
        timeout: int = 30,
        circuit_breaker_enabled: bool = True,
    ):
        self._github_client: Optional[Github] = None
        self._retry_handler = get_retry_handler(max_retries=max_retries)
        self._circuit_breaker = get_circuit_breaker() if circuit_breaker_enabled else None
    
    def initialize_client(self, github_token: Optional[str] = None) -> None:
        if github_token:
            self._github_client = Github(auth=Token(github_token))
        else:
            self._github_client = Github()
    
    def get_repository(self, repo_full_name: str):
        '''Wrapped with retry + circuit breaker'''
        return self._retry_handler.retry_sync(
            lambda: self._github_client.get_repo(repo_full_name)
        )
```

### ETag Adapter (HTTP 304 Conditional Requests)
```python
class ETagAdapter:
    '''Store/compare ETags for bandwidth reduction'''
    
    def __init__(self):
        self._etag_cache: dict[str, str] = {}
    
    def get_cached_etag(self, url: str) -> Optional[str]:
        return self._etag_cache.get(url)
    
    def store_etag(self, url: str, etag: str) -> None:
        self._etag_cache[url] = etag
    
    def request_with_etag(self, url: str) -> tuple[Optional[str], bool]:
        '''Returns (data, is_cached). If 304, data is None and is_cached=True'''
        etag = self.get_cached_etag(url)
        headers = {'If-None-Match': etag} if etag else {}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 304:
            return None, True  # Use cached data
        
        new_etag = response.headers.get('ETag')
        if new_etag:
            self.store_etag(url, new_etag)
        
        return response.text, False
```

### Rate Limiting Handler
```python
def handle_rate_limit_error(exception):
    '''Detect 403/429 and apply smart retry'''
    if hasattr(exception, 'status') and exception.status in [403, 429]:
        reset_time = exception.headers.get('X-RateLimit-Reset')
        wait_time = calculate_wait_time(reset_time)
        time.sleep(wait_time)
        return True  # Retryable
    return False
```

## Anti-Patterns

- ❌ Direct PyGithub calls without retry wrapper
- ❌ Missing circuit breaker for fault tolerance
- ❌ Retrying 404s for file content (not transient)
- ❌ Ignoring rate limit headers (403/429)
- ❌ No ETag support (wasted bandwidth)

## Files

- `api_client.py`: Main GitHub API client (retry + circuit breaker)
- `etag_adapter.py`: ETag support for HTTP 304
- `diff_generator.py`: Diff generation with file content
- `file_processor.py`: File processing and filtering
