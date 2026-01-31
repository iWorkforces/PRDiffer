# AGENTS.md - Infrastructure/Factories

Factories for creating infrastructure dependencies with proper DI wiring.

## Guidelines

- Create configured infrastructure instances
- Handle dependency wiring via ServiceContainer
- Support configuration overrides
- Return interfaces, not concrete types where possible
- **15+ `get_*()` factory functions** for lazy initialization

## Common Patterns

### Singleton Factory with Manual Caching
```python
import threading

_github_service = None
_github_lock = threading.RLock()

def get_github_service(
    token: Optional[str] = None,
    timeout: int = 30,
) -> GitHubAPIServiceInterface:
    '''Lazy singleton with double-check locking'''
    global _github_service
    if _github_service is None:
        with _github_lock:
            if _github_service is None:
                client = GitHubAPIClient(timeout=timeout)
                if token:
                    client.initialize_client(github_token=token)
                _github_service = client
    return _github_service
```

### Infrastructure Factory (Dependency Inversion)
```python
from prdiffer.domain.factories import InfrastructureFactoryInterface

class InfrastructureFactory(InfrastructureFactoryInterface):
    '''Implements domain factory interface (dependency inversion)'''
    
    @staticmethod
    def create_github_client(**kwargs) -> GitHubAPIServiceInterface:
        '''Return interface, not concrete type'''
        return GitHubAPIClient(**kwargs)
    
    @staticmethod
    def create_cache_service() -> CacheServiceInterface:
        return CacheService()
    
    @staticmethod
    def create_retry_handler() -> RetryHandlerInterface:
        return UnifiedRetryHandler()
```

### ServiceContainer Integration
```python
from prdiffer.infrastructure.di_container import ServiceContainer

def wire_dependencies():
    '''Register all infrastructure services in DI container'''
    container = ServiceContainer.get_instance()
    
    # Register singletons
    container.register_singleton('github_service', lambda: get_github_service())
    container.register_singleton('cache_service', lambda: get_cache_service())
    
    # Register transient (new instance each time)
    container.register_transient('retry_handler', lambda: UnifiedRetryHandler())
```

## Anti-Patterns

- ❌ Complex logic in factories (keep simple, just object creation)
- ❌ Returning concrete types from factory interfaces
- ❌ Missing input validation before construction
- ❌ Factory methods with side effects
- ❌ Using @lru_cache for settings (use manual RLock pattern)

## Files

- `infrastructure_factory.py`: Main infrastructure factory (dependency inversion)
