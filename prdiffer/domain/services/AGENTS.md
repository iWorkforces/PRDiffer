# AGENTS.md - Domain/Services

Business logic interfaces and service contracts.

## Guidelines

- Define service interfaces (no implementation)
- Use ABC or Protocol for definitions
- All public methods require type hints
- Async methods named with `_async` suffix

## Common Patterns

### Service Interface
```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class GitHubAPIServiceInterface(ABC):
    @abstractmethod
    def get_repository(self, repo_full_name: str) -> Optional[Repository]:
        pass
    
    @abstractmethod
    def get_file_content(
        self, repository: Repository, file_path: str, branch: str
    ) -> str:
        pass
```

### Service with Error Handling
```python
class DiffServiceInterface(ABC):
    @abstractmethod
    def generate_diff(
        self, owner: str, repo: str, pr_number: int
    ) -> PRDiff:
        pass
    
    @abstractmethod
    def validate_diff(self, diff: PRDiff) -> bool:
        pass
```

## Files

- `github_api.py`: GitHub API service interface
- `cache.py`: Cache service interface
- `logger.py`: Logger interface
- `diff.py`: Diff generation service interface
- `pr_diff_service.py`: PR diff service interface
- `retry.py`: Retry policy interface
- `repository_cache.py`: Repository cache interface
- `pattern_matching.py`: Pattern matching interface
- `settings.py`: Settings service interface
