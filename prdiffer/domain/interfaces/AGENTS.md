# AGENTS.md - Domain/Interfaces

Protocol definitions and abstract base classes for domain contracts.

## Guidelines

- Use ABC (Abstract Base Classes) or Protocol
- Define method signatures only, no implementation
- All methods must be @abstractmethod
- Type hints required on all methods
- **Dual sync/async methods** → Both `method()` and `method_async()`
- **Interface segregation** → Small, focused interfaces

## Common Patterns

### Protocol Definition
```python
from typing import Protocol, Optional
from github.Repository import Repository
from github.PullRequest import PullRequest

class GitHubAPIServiceInterface(Protocol):
    def get_repository(self, repo_full_name: str) -> Optional[Repository]:
        ...
    
    def get_pull_request(
        self, repository: Repository, pr_number: int
    ) -> Optional[PullRequest]:
        ...
```

### Abstract Base Class with Dual APIs
```python
from abc import ABC, abstractmethod

class RetryHandlerInterface(ABC):
    '''Dual sync/async interface pattern'''
    
    @abstractmethod
    def retry_sync(self, func, *args, **kwargs):
        '''Synchronous retry with backoff'''
        pass
    
    @abstractmethod
    async def retry_async(self, func, *args, **kwargs):
        '''Async retry with backoff'''
        pass
```

### Cache Service Interface
```python
from abc import ABC, abstractmethod

class CacheServiceInterface(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass
    
    @abstractmethod
    def invalidate(self, key: str) -> None:
        pass
```

## Anti-Patterns

- ❌ Implementing logic in interfaces (use ABC/Protocol only)
- ❌ Missing @abstractmethod decorators
- ❌ Large interfaces (violates interface segregation)
- ❌ Concrete types in method signatures (use interfaces)

## Files

- `protocols.py`: Core service protocols
- `vcs_provider.py`: VCSDiffRepositoryInterface
