# AGENTS.md - Application/Components

MCP server components (authentication, rate limiting, health monitoring, metrics, operation handler, plugin manager).

## Guidelines

- Single responsibility per component
- Use domain service interfaces
- Use dependency injection for testability (ServiceContainer, ServiceFactory)
- Log operations with sanitized data
- Return structured responses

## Common Patterns

### Component with DI
```python
from prdiffer.infrastructure.di_container import get_container
from prdiffer.infrastructure.service_factory import get_service_factory
from prdiffer.domain.services.logger import LoggerServiceInterface

class SomeComponent:
    def __init__(self, container=None, logger=None):
        self._container = container or get_container()
        factory = get_service_factory(logger=logger)
        self._logger = logger or factory.get_logger()
```

### Component Factory Pattern
```python
def create_component(container=None, logger=None):
    factory = get_service_factory(logger=logger)
    container = container or get_container()
    return SomeComponent(
        container=container,
        logger=logger or factory.get_logger()
    )
```

## Component Descriptions

### AuthenticationMiddleware
- API key-based authentication with SHA-256 hashing
- JWT token verification
- Admin API key support with elevated privileges
- Per-client rate limiting and lockout mechanism
- Runtime API key management (add/remove)
- Thread-safe operations with RLock

### RateLimiter
- Token bucket algorithm: 100 requests per minute per client
- Automatic cleanup of inactive clients (1 hour TTL)
- Global rate monitoring across all clients
- Thread-safe operations with RLock

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
- URL parsing with regex: `r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"`
- Lazy repository initialization
- Coordinates MetricsTracker, RateLimiter, HealthMonitor for PR operations

### PluginManager
- Plugin discovery and registration
- Enabled/disabled state management
- Tool execution orchestration
- Supports MCP tool plugins via MCPToolPlugin interface
- Auto-discovers plugins from `prdiffer.application.plugins`

## Files

- `authentication.py`: API key authentication with SHA-256 hashing
- `rate_limiter.py`: Per-client rate limiting
- `metrics_tracker.py`: Request metrics tracking
- `health_monitor.py`: Server health checks
- `server_configuration.py`: Runtime configuration
- `pr_operation_handler.py`: PR operations coordination
- `factory.py`: Component wiring and injection
- `plugin_manager.py`: Plugin system manager (NEW)

## Plugin System (NEW)

### Plugin Interface
- Location: `prdiffer.application.interfaces.tool_plugin`
- Interface: `MCPToolPlugin`
- Properties: `name`, `description`, `parameters`
- Methods: `enabled()`, `execute(**kwargs)`

### Plugin Manager
- Location: `prdiffer.application.plugin_manager`
- Class: `PluginManager`
- Methods:
  - `register_plugin(plugin)` - Register a plugin
  - `unregister_plugin(name)` - Unregister a plugin
  - `get_plugin(name)` - Get plugin instance
  - `list_plugins()` - List all registered plugins
  - `list_plugin_names()` - List plugin names
  - `execute_tool(tool_name, **kwargs)` - Execute a plugin tool

### Plugin Implementations
- Location: `prdiffer.application.plugins/`
- Example: `get_pr_diff_plugin.py` - Get PR diff as MCP tool

### Usage Pattern
```python
from prdiffer.application.plugin_manager import PluginManager

manager = PluginManager()

# Get plugin and execute
plugin = manager.get_plugin("get_pr_diff")
result = await plugin.execute(pr_url="https://github.com/owner/repo/pull/123")

# List all available plugins
plugins = manager.list_plugin_names()
for name in plugins:
    print(f"Available plugin: {name}")
```
