# AGENTS.md - Infrastructure/Interfaces

Infrastructure-level protocol definitions (rare, most interfaces in domain).

## Guidelines

- Define infrastructure-specific interfaces (uncommon)
- **Most interfaces should be in domain layer** (Clean Architecture)
- Protocol for external service adaptations
- Type hints for infrastructure components
- **Use only when interface is infrastructure-specific** (e.g., HTTP clients, database adapters)

## Common Patterns

### Infrastructure Protocol (Rare)
```python
from typing import Protocol

class HTTPClientInterface(Protocol):
    '''Infrastructure-specific interface (not business logic)'''
    
    def get(self, url: str, headers: dict) -> dict:
        ...
    
    def post(self, url: str, data: dict, headers: dict) -> dict:
        ...
```

### Adapter Interface (Hexagonal Architecture)
```python
from abc import ABC, abstractmethod

class DatabaseAdapterInterface(ABC):
    '''Infrastructure adapter for persistence'''
    
    @abstractmethod
    def connect(self) -> None:
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        pass
```

## When to Use

- **Infrastructure-specific contracts** (HTTP clients, DB adapters)
- **External service adapters** (third-party API wrappers)
- **Platform-specific interfaces** (OS-specific operations)

## When NOT to Use

- ❌ Business logic interfaces (use domain/interfaces/)
- ❌ Service contracts (use domain/services/)
- ❌ Repository patterns (use domain/repositories/)

## Anti-Patterns

- ❌ Defining business logic interfaces in infrastructure
- ❌ Large interfaces (violates interface segregation)
- ❌ Missing Protocol/ABC decorators

## Files

- (Various protocol definitions as needed - uncommon)
