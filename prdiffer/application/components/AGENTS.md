# AGENTS.md - Application/Components

MCP server components with constructor DI pattern (`container=None` for testability).

## Guidelines

- Single responsibility per component
- Use domain service interfaces (not concrete infrastructure types)
- **Constructor DI with singleton fallbacks:** `container=None, logger=None`
- Log operations with sanitized data (no tokens/passwords)
- Return structured responses (Pydantic models)
- **Thread-safe operations** (RLock for sync, anyio.Lock for async)

## Common Patterns

### Component with Optional DI (Testability)
```python
from prdiffer.infrastructure.di_container import get_container
from prdiffer.infrastructure.service_factory import get_service_factory
from prdiffer.domain.services.logger import LoggerServiceInterface

class SomeComponent:
    '''Constructor DI with singleton fallbacks for testability'''
    
    def __init__(self, container=None, logger=None):
        self._container = container or get_container()
        factory = get_service_factory(logger=logger)
        self._logger = logger or factory.get_logger()
```

### Component Factory Pattern
```python
def create_component(container=None, logger=None):
    '''Factory function for component creation'''
    factory = get_service_factory(logger=logger)
    container = container or get_container()
    return SomeComponent(
        container=container,
        logger=logger or factory.get_logger()
    )
```

### Thread-Safe Component (RLock)
```python
import threading

class RateLimiter:
    '''Thread-safe rate limiter with RLock'''
    
    def __init__(self):
        self._lock = threading.RLock()
        self._clients = {}
    
    def check_rate_limit(self, client_id: str) -> bool:
        with self._lock:
            # Thread-safe access
            return self._clients.get(client_id, 0) < 100
```

## Component Descriptions

### AuthenticationMiddleware
- **API key-based authentication** with SHA-256 hashing
- **JWT token verification** (metadata extraction only, not auth decisions)
- Admin API key support with elevated privileges
- Per-client rate limiting and lockout mechanism
- Runtime API key management (add/remove)
- **Thread-safe operations** with RLock
- **Architecture violation:** Directly imports `infrastructure.security.input_validator`

### RateLimiter
- **Token bucket algorithm:** 100 requests per minute per client
- Automatic cleanup of inactive clients (1 hour TTL)
- Global rate monitoring across all clients
- **Thread-safe operations** with RLock

### MetricsTracker
- Request counting (total, successful, failed)
- Operation-specific metrics (execution time, success rate)
- Uptime tracking with human-readable format
- Request ID generation (REQ-{timestamp}-{counter})

### HealthMonitor
- Aggregates metrics from MetricsTracker and RateLimiter
- Health status: healthy/degraded/unhealthy
- Status thresholds: success rate < 80% OR remaining rate limit < 10% = degraded
- GitHub API health checking via GitHubAPIClient

### ServerConfiguration
- Logging configuration from settings
- Transport validation (stdio, http, sse, streamable-http)
- Port validation (1-65535 for non-stdio transports)
- Configuration validation with warnings/errors

### PROperationHandler
- PR diff fetching via GitHub API
- Repository caching for efficiency
- URL parsing with regex: `r'https://github\\.com/([^/]+)/([^/]+)/pull/(\\d+)'`
- Lazy repository initialization
- Coordinates MetricsTracker, RateLimiter, HealthMonitor for PR operations
- **Architecture violation:** Imports infrastructure services directly

### PluginManager
- Plugin discovery and registration
- Enabled/disabled state management
- Tool execution orchestration
- Supports MCP tool plugins via MCPToolPlugin interface
- Auto-discovers plugins from `prdiffer.application.plugins`
- **Current state:** Exists but not integrated (production uses @mcp.tool())

## Anti-Patterns

- ❌ Direct infrastructure imports (9 violations in authentication.py, etc.)
- ❌ Business logic in components (belongs in domain)
- ❌ Missing thread safety (use RLock/anyio.Lock)
- ❌ Logging sensitive data (tokens, passwords, API keys)
- ❌ Mutable global state (use ServiceContainer)

## Files

- `authentication.py`: API key authentication with SHA-256 hashing (9 violations)
- `rate_limiter.py`: Per-client rate limiting
- `metrics_tracker.py`: Request metrics tracking
- `health_monitor.py`: Server health checks
- `server_configuration.py`: Runtime configuration
- `pr_operation_handler.py`: PR operations coordination (violations)
- `plugin_manager.py`: Plugin system manager (not yet integrated)
