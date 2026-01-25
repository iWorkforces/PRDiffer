# AGENTS.md - Domain Layer

Pure business logic layer. No external dependencies, frameworks, or I/O operations.

## Guidelines

- Pure Python - no imports from `infrastructure` or `application`
- Define interfaces/contracts only, not implementations
- Entities: immutable data models with validation
- Services: business logic without side effects
- Use Pydantic for data validation (BaseModel)
- Exceptions: define hierarchy in `exceptions.py`
- Error codes: structured codes in `errors.py`

## Common Patterns

### Entities
```python
from pydantic import BaseModel, Field

class PRDiff(BaseModel):
    diff_content: str = Field(default="", description="Combined diff content")

    @property
    def has_content(self) -> bool:
        return bool(self.diff_content and self.diff_content.strip())
```

### Service Interfaces
```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class GitHubAPIServiceInterface(ABC):
    @abstractmethod
    def get_repository(self, repo_full_name: str) -> Optional[Repository]:
        pass
```

### Custom Exceptions
```python
class PRDifferException(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details: Dict[str, Any] = details or {}
```

## Files Reference

- `entities/`: Domain models (PRDiff, FilePatchInfo)
- `services/`: Business logic interfaces
- `repositories/`: Data access contracts
- `interfaces/`: Protocol definitions
- `exceptions.py`: Custom exception hierarchy
- `errors.py`: Structured error codes (E{category}{number}_{NAME})
- `vcs_provider_registry.py`: VCS provider registry for multi-provider support

## VCS Provider Registry

The `vcs_provider_registry.py` module provides centralized VCS provider management:

### Purpose
- Auto-detect VCS provider from repository URLs
- Register and retrieve VCS implementations
- Support multiple VCS platforms (GitHub, GitLab, Bitbucket, etc.)

### Usage Pattern
```python
from prdiffer.domain.vcs_provider_registry import VCSProviderRegistry

registry = VCSProviderRegistry()

# Auto-detect provider from URL
provider = registry.get_provider(url="https://github.com/owner/repo/pull/123")
if provider:
    diff = await provider.get_pr_diff()
```

### Adding New VCS Providers

1. Implement `VCSDiffRepositoryInterface` in `prdiffer/infrastructure/vcs_providers/`
2. Register provider in `VCSProviderRegistry` using:
   - `register_provider(name, provider_class, url_pattern)`
   - `supports_repository(url)` method to match URLs
3. Add imports to `prdiffer/domain/vcs_provider_registry.py`

### Current Providers
- GitHub: `prdiffer.infrastructure.vcs_providers.github_repository.GitHubVCSRepository`
- GitLab: `prdiffer.infrastructure.vcs_providers.gitlab_repository.GitLabVCSRepository`
