# AGENTS.md - Domain/Config

Configuration interfaces and types for the domain layer.

## Guidelines

- Define configuration interfaces (ABC/Protocol)
- No concrete implementations here
- Type hints for configuration values
- Use Pydantic for config models if needed

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

### Config Model
```python
from pydantic import BaseModel

class GitHubConfig(BaseModel):
    rate_limit: int = 5000
    timeout: int = 30
    max_retries: int = 3
```

## Files

- `github_config.py`: GitHub API configuration
- `github_config_interface.py`: Abstract interface for GitHub config
