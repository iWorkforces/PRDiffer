# AGENTS.md - Domain/Repositories

Data access contracts and repository interfaces.

## Guidelines

- Define repository interfaces only
- No concrete implementations
- Use Protocol or ABC for definitions
- Async methods should have `_async` suffix in interface

## Common Patterns

### Repository Protocol
```python
from typing import Protocol, Optional
from prdiffer.domain.entities import PRDiff

class PRDiffRepositoryInterface(Protocol):
    def get_diff(self, owner: str, repo: str, pr_number: int) -> Optional[PRDiff]:
        ...
    
    def save_diff(self, pr_diff: PRDiff) -> None:
        ...
```

### Async Repository
```python
class AsyncPRDiffRepositoryInterface(Protocol):
    async def get_diff_async(
        self, owner: str, repo: str, pr_number: int
    ) -> Optional[PRDiff]:
        ...
```

## Files

- `pr_diff_repository.py`: PR diff repository interface
