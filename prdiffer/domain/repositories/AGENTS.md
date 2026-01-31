# AGENTS.md - Domain/Repositories

Data access contracts and repository interfaces.

## Guidelines

- Define repository interfaces only (no implementations)
- No concrete implementations in domain
- Use Protocol or ABC for definitions
- Async methods should have `_async` suffix in interface
- **Repository pattern:** Abstract data access operations
- **Dual sync/async methods** for infrastructure flexibility

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
    
    def delete_diff(self, owner: str, repo: str, pr_number: int) -> None:
        ...
```

### Async Repository
```python
class AsyncPRDiffRepositoryInterface(Protocol):
    async def get_diff_async(
        self, owner: str, repo: str, pr_number: int
    ) -> Optional[PRDiff]:
        ...
    
    async def save_diff_async(self, pr_diff: PRDiff) -> None:
        ...
```

### VCS Repository Interface
```python
from abc import ABC, abstractmethod

class VCSDiffRepositoryInterface(ABC):
    '''VCS provider contract for multi-provider support'''
    
    @abstractmethod
    def supports_repository(self, url: str) -> bool:
        '''Auto-detect if this provider supports the URL'''
        pass
    
    @abstractmethod
    def get_pr_diff(self, url: str) -> PRDiff:
        pass
```

## Anti-Patterns

- ❌ Implementing data access in domain (use infrastructure)
- ❌ Missing async variants (_async suffix)
- ❌ Large repository interfaces (interface segregation)
- ❌ Concrete database/API calls in domain

## Files

- `pr_diff_repository.py`: PR diff repository interface
