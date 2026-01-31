# AGENTS.md - Application/Services

Application-level service implementations (orchestration layer).

## Guidelines

- Orchestrate domain and infrastructure services (no business logic)
- Handle application-level concerns (logging, request pipeline, error translation)
- Return structured responses (Pydantic models)
- **Use constructor DI** with singleton fallbacks (ServiceContainer, ServiceFactory)
- **No business logic** → Domain layer only

## Common Patterns

### Application Service (Orchestration)
```python
from prdiffer.domain.services import GitHubAPIServiceInterface
from prdiffer.infrastructure.logging.logger_factory import LazyLoggerMixin

class PRApplicationService(LazyLoggerMixin):
    '''Orchestrates domain + infrastructure services (no business logic)'''
    
    def __init__(self, github_service: GitHubAPIServiceInterface):
        self._github_service = github_service
    
    async def get_pr_details(self, pr_url: str) -> dict:
        '''Orchestration: log → call domain service → return'''
        self._logger.info(f'Fetching PR details: {pr_url}')
        result = await self._github_service.get_pr_diff(pr_url)
        return {'pr_diff': result}
```

### Service with Optional DI (Testability)
```python
from prdiffer.infrastructure.di_container import get_container
from prdiffer.infrastructure.service_factory import get_service_factory
from prdiffer.domain.services.logger import LoggerServiceInterface

class SomeService:
    '''Constructor DI with singleton fallbacks'''
    
    def __init__(self, container=None, logger=None):
        self._container = container or get_container()
        factory = get_service_factory(logger=logger)
        self._logger = logger or factory.get_logger()
        self._settings = factory.get_settings_service()
```

### Request Pipeline Pattern
```python
class RequestPipelineService:
    '''Application-level request orchestration'''
    
    def __init__(
        self,
        auth: AuthenticationMiddleware,
        rate_limiter: RateLimiter,
        metrics: MetricsTracker,
    ):
        self._auth = auth
        self._rate_limiter = rate_limiter
        self._metrics = metrics
    
    async def process_request(self, request: dict) -> dict:
        # 1. Authenticate
        client_id = self._auth.authenticate(request)
        
        # 2. Rate limit check
        if not self._rate_limiter.check_rate_limit(client_id):
            raise RateLimitExceeded()
        
        # 3. Track metrics
        request_id = self._metrics.start_request()
        
        # 4. Execute business logic
        result = await self._execute_business_logic(request)
        
        # 5. End tracking
        self._metrics.end_request(request_id)
        
        return result
```

## Anti-Patterns

- ❌ Business logic in application services (belongs in domain)
- ❌ Direct infrastructure calls (inject via DI)
- ❌ Large orchestration methods (break into smaller services)
- ❌ Missing error translation (domain → application errors)

## Files

- `github_api.py`: GitHub API service implementation (if exists)
- `pr_diff_service.py`: PR diff service implementation (if exists)

## Note on Plugin System

The application layer includes a plugin system for MCP tools (MCPToolPlugin). Many features previously in services may migrate to plugins for better modularity. See `plugins/AGENTS.md` for details.

**Current state:** Plugin system exists but production uses `@mcp.tool()` decorators directly in `mcp_server.py`.
