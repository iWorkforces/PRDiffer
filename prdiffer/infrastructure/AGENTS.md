# AGENTS.md - Infrastructure Layer

External integrations: GitHub API, caching, logging, utilities, VCS providers.

## Guidelines

- Implement domain interfaces
- Handle I/O, network, filesystem operations
- Use PyGithub for GitHub API
- Implement retry logic with circuit breaker
- Log with sanitized sensitive data
- Use dependency injection for testability (ServiceContainer, ServiceFactory)
- Support multiple VCS providers (GitHub, GitLab, extensible)

## Common Patterns

### Infrastructure Service with DI
```python
from prdiffer.domain.services import LoggerServiceInterface
from prdiffer.infrastructure.di_container import get_container
from prdiffer.infrastructure.service_factory import get_service_factory

class SomeInfrastructureService:
    def __init__(self, container=None, logger=None):
        self._container = container or get_container()
        factory = get_service_factory(logger=logger)
        self._logger = logger or factory.get_logger()
```

### Using ServiceContainer
```python
from prdiffer.infrastructure.di_container import get_container
from prdiffer.domain.services.logger import LoggerServiceInterface

class SomeClass:
    def __init__(self, container=None):
        self._container = container or get_container()
        self._logger = self._container.get(LoggerServiceInterface)
```

### Using ServiceFactory
```python
from prdiffer.infrastructure.service_factory import get_service_factory

def get_some_service():
    factory = get_service_factory()
    return factory.get_some_service()
```

## Subdirectories

- `github/`: GitHub API client implementation
- `vcs_providers/`: Multi-provider VCS abstraction (GitHub, GitLab, extensible)
- `utils/`: Utility functions and helpers
- `logging/`: Logging infrastructure
- `security/`: Security utilities
- `factories/`: Infrastructure factories
- `services/`: Infrastructure services

## Key Files

### Dependency Injection
- `di_container.py`: Dependency injection container (ServiceContainer)
  - `register_singleton()`: Register singleton services
  - `register_transient()`: Register transient services
  - `get()`: Get service instance
  - Thread-safe operations with Lock

- `service_factory.py`: Service factory for dependency injection
  - `get_service_factory()`: Get or create global factory
  - Provides centralized service creation
  - Supports optional dependency injection

### VCS Provider System
- `domain/vcs_provider_registry.py`: VCS provider registry in domain layer
  - `domain/interfaces/vcs_provider.py`: VCSDiffRepositoryInterface

- `vcs_providers/github_repository.py`: GitHub VCS provider
  - Implements VCSDiffRepositoryInterface
  - Wraps GitHubPRDiffRepository with backward compatibility

- `vcs_providers/gitlab_repository.py`: GitLab VCS provider (mock/stub)
  - Implements VCSDiffRepositoryInterface
  - Extensible pattern for adding more providers

### GitHub Components
- `github_repository.py`: GitHub repository implementation with DI support
  - Accepts optional: settings_service, logger, input_validator
  - Uses factory functions for components
  - Maintains backward compatibility with singleton fallbacks

### Other Key Services
- `repository_cache_service.py`: Cache service for repository data
- `cache_service.py`: Generic cache implementation
- `settings.py`: Configuration service (uses dynaconf)
- `async_parallel_executor.py`: Parallel execution utility with anyio
- `request_coalescing.py`: Request deduplication service

## New Architecture Features (v0.4.9)

### Multi-Provider VCS Support
- Auto-detection of VCS provider from repository URLs
- Centralized provider registry in domain layer
- Extensible provider registration pattern
- Support for GitHub and GitLab with foundation for more providers

### Dependency Injection Infrastructure
- ServiceContainer with singleton and transient service lifecycles
- ServiceFactory for centralized service creation
- Constructor injection support throughout infrastructure
- Backward compatible with singleton fallbacks
