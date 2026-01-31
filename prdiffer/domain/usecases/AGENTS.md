# AGENTS.md - Domain/Usecases

Use cases orchestrating domain logic.

## Guidelines

- Single responsibility per use case
- No I/O operations directly (use services via DI)
- Return domain entities or value objects
- Error handling via exceptions
- **Inject services via constructor** (DI pattern)
- **Orchestrate, don't implement** → Call services, don't do I/O

## Common Patterns

### Use Case with DI
```python
from typing import Optional
from prdiffer.domain.entities import PRDiff
from prdiffer.domain.services import GitHubAPIServiceInterface, CacheServiceInterface

class GetPRDiffUseCase:
    '''Use case orchestrates services via dependency injection'''
    
    def __init__(
        self,
        github_service: GitHubAPIServiceInterface,
        cache_service: CacheServiceInterface,
    ):
        self._github_service = github_service
        self._cache_service = cache_service
    
    def execute(self, pr_url: str) -> Optional[PRDiff]:
        # 1. Parse URL
        # 2. Check cache
        # 3. Fetch from GitHub if needed
        # 4. Update cache
        # 5. Return result
        pass
```

### Use Case with Error Handling
```python
from prdiffer.domain.exceptions import PRDifferException

class GetPRDiffUseCase:
    def execute(self, pr_url: str) -> PRDiff:
        try:
            return self._github_service.get_pr_diff(pr_url)
        except Exception as e:
            raise PRDifferException(f'Failed to get PR diff: {e}')
```

## Anti-Patterns

- ❌ Direct I/O operations (use services)
- ❌ Multiple responsibilities (single use case per class)
- ❌ Business logic in use case (belongs in entities/services)
- ❌ Missing dependency injection (pass services via constructor)

## Files

- `pr_diff_usecases.py`: PR diff related use cases
