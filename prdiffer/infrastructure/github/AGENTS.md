# AGENTS.md - Infrastructure/GitHub

GitHub API client and related implementations.

## Guidelines

- Use PyGithub library for API calls
- Implement retry logic with exponential backoff
- Circuit breaker for fault tolerance
- Cache file contents with TTL
- Handle rate limiting

## Common Patterns

### API Client
```python
from github import Github
from prdiffer.domain.services import GitHubAPIServiceInterface

class GitHubAPIClient(GitHubAPIServiceInterface):
    def __init__(
        self,
        max_retries: int = 3,
        timeout: int = 30,
        circuit_breaker_enabled: bool = True,
    ):
        self._github_client: Optional[Github] = None
        self._retry_handler = get_retry_handler(max_retries=max_retries)
    
    def initialize_client(self, github_token: Optional[str] = None) -> None:
        if github_token:
            from github.Auth import Token
            self._github_client = Github(auth=Token(github_token))
        else:
            self._github_client = Github()
```

## Files

- `api_client.py`: Main GitHub API client
- `diff_generator.py`: Diff generation
- `file_processor.py`: File processing
