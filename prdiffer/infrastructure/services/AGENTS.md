# AGENTS.md - Infrastructure/Services

Infrastructure-level service implementations.

## Guidelines

- Implement domain interfaces
- Handle external API/service integrations
- Add retry, caching, error handling
- Log operations appropriately

## Common Patterns

### Infrastructure Service
```python
from prdiffer.domain.services import CacheServiceInterface

class CacheService(CacheServiceInterface):
    def __init__(self, default_ttl: int = 300):
        self._cache = {}
        self._ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._cache[key] = value
```

## Files

- `pr_diff_service.py`: PR diff infrastructure service
