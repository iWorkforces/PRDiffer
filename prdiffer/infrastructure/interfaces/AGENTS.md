# AGENTS.md - Infrastructure/Interfaces

Infrastructure-level protocol definitions.

## Guidelines

- Define infrastructure-specific interfaces
- Protocol for external service adaptations
- Type hints for infrastructure components

## Common Patterns

### Infrastructure Protocol
```python
from typing import Protocol

class HTTPClientInterface(Protocol):
    def get(self, url: str) -> dict:
        ...
    
    def post(self, url: str, data: dict) -> dict:
        ...
```

## Files

- (Various protocol definitions as needed)
