# AGENTS.md - Application/Services

Application-level service implementations.

## Guidelines

- Orchestrate domain and infrastructure services
- Handle application-level concerns (logging, errors)
- Return structured responses
- Use dependency injection for testability (ServiceContainer, ServiceFactory)

## Common Patterns

### Application Service
```python
from prdiffer.domain.services import GitHubAPIServiceInterface

class PRApplicationService:
    def __init__(self, github_service: GitHubAPIServiceInterface):
        self._github_service = github_service

    def get_pr_details(self, pr_url: str) -> dict:
        return self._github_service.get_repository(pr_url)
```

### Service with DI
```python
from prdiffer.infrastructure.di_container import get_container
from prdiffer.infrastructure.service_factory import get_service_factory
from prdiffer.domain.services.logger import LoggerServiceInterface

class SomeService:
    def __init__(self, container=None, logger=None):
        self._container = container or get_container()
        factory = get_service_factory(logger=logger)
        self._logger = logger or factory.get_logger()
        self._settings = factory.get_settings_service()
```

## Files

- `github_api.py`: GitHub API service implementation
- `pr_diff_service.py`: PR diff service implementation

## Note on Plugin System

The application layer now includes a plugin system for MCP tools. Many features previously in services may be migrated to plugins. See `components/AGENTS.md` for plugin architecture details.
