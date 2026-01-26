# AGENTS.md - Domain/Interfaces

Protocol definitions and abstract base classes for domain contracts.

## Guidelines

- Use ABC (Abstract Base Classes) or Protocol
- Define method signatures only, no implementation
- All methods must be @abstractmethod
- Type hints required on all methods

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

### Abstract Base Class
```python
from abc import ABC, abstractmethod

class CacheServiceInterface(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass
```

## Files

- `protocols.py`: Core service protocols
