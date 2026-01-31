# AGENTS.md - Domain/Config

Configuration interfaces and types for the domain layer.

## Guidelines

- Define configuration interfaces (ABC/Protocol)
- No concrete implementations here
- Type hints for configuration values
- Use Pydantic for config models if needed
- **Frozen dataclasses with `tuple` fields** (not `list`) for hashability

## Common Patterns

### Config Interface
```python
from abc import ABC
from typing import Optional

class GitHubConfigInterface(ABC):
    @property
    @abstractmethod
    def rate_limit(self) -> int:
        pass
    
    @property
    @abstractmethod
    def timeout(self) -> int:
        pass
```

### Frozen Config Model (Hashable)
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class GitHubConfig:
    '''Frozen dataclass for hashability (used in manual caching)'''
    rate_limit: int = 5000
    timeout: int = 30
    max_retries: int = 3
    ignore_patterns: tuple[str, ...] = ()  # NOT list
    valid_extensions: tuple[str, ...] = ('.py', '.js', '.ts')
```

### Pydantic Config Model
```python
from pydantic import BaseModel

class GitHubConfig(BaseModel):
    rate_limit: int = 5000
    timeout: int = 30
    max_retries: int = 3
```

## Anti-Patterns

- ❌ Using `list` in frozen dataclasses (not hashable)
- ❌ Concrete implementations in domain/config (use infrastructure)
- ❌ Missing type hints on config properties
- ❌ Mutable config objects (prefer frozen)

## Files

- `github_config.py`: GitHub API configuration (frozen dataclass)
- `github_config_interface.py`: Abstract interface for GitHub config
