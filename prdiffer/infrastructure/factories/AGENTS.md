# AGENTS.md - Infrastructure/Factories

Factories for creating infrastructure dependencies.

## Guidelines

- Create configured infrastructure instances
- Handle dependency wiring
- Support configuration overrides
- Return interfaces, not concrete types where possible

## Common Patterns

### Factory Function
```python
from prdiffer.infrastructure.github import GitHubAPIClient
from prdiffer.domain.services import GitHubAPIServiceInterface

def create_github_service(
    token: Optional[str] = None,
    timeout: int = 30,
) -> GitHubAPIServiceInterface:
    client = GitHubAPIClient(timeout=timeout)
    if token:
        client.initialize_client(github_token=token)
    return client
```

### Infrastructure Factory
```python
class InfrastructureFactory:
    @staticmethod
    def create_github_client(**kwargs) -> GitHubAPIClient:
        return GitHubAPIClient(**kwargs)
    
    @staticmethod
    def create_cache_service() -> CacheService:
        return CacheService()
```

## Files

- `infrastructure_factory.py`: Main infrastructure factory
