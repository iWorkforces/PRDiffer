# AGENTS.md - Domain/Usecases

Use cases orchestrating domain logic.

## Guidelines

- Single responsibility per use case
- No I/O operations directly (use services)
- Return domain entities or value objects
- Error handling via exceptions

## Common Patterns

### Use Case Class
```python
from typing import Optional
from prdiffer.domain.entities import PRDiff
from prdiffer.domain.services import GitHubAPIServiceInterface, CacheServiceInterface

class GetPRDiffUseCase:
    def __init__(
        self,
        github_service: GitHubAPIServiceInterface,
        cache_service: CacheServiceInterface,
    ):
        self._github_service = github_service
        self._cache_service = cache_service
    
    def execute(self, pr_url: str) -> Optional[PRDiff]:
        # Parse URL, get from cache or fetch
        pass
```

## Files

- `pr_diff_usecases.py`: PR diff related use cases
