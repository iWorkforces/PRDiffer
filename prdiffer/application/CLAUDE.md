# CLAUDE.md - Application Layer

This file provides guidance for working with the Application Layer of PRDiffer.

**Current Version:** 0.4.9

## OVERVIEW
FastMCP server setup, MCP tool plugins, component wiring, dependency injection orchestration. MCP server, FastMCP components, plugin system, orchestration.

**Architecture:**
- FastMCP server (615 lines) with 13 injected dependencies
- 7 application components with protocol-based interfaces
- Factory-based dependency injection for loose coupling
- Comprehensive security with authentication and rate limiting

## STRUCTURE
```
prdiffer/application/
├── components/         # MCP components (auth, rate limiting, health, metrics)
├── plugins/            # MCP tool plugins
├── interfaces/         # MCP-specific protocols
├── mcp_server.py       # FastMCP server
├── plugin_manager.py   # Plugin discovery
└── factory.py          # Application factory
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add MCP tool** | `plugins/` | Implement MCPToolPlugin |
| **Add component** | `components/` | Accept dependencies via DI |
| **Register plugin** | `plugin_manager.py` | Use register_plugin() |

## CONVENTIONS

### MCP Tools
- Use FastMCP @mcp.tool() decorator
- Return Pydantic models
- Use PROperationHandler for PR operations

### Components
- Constructor injection
- Health check methods
- Metrics tracking

### Plugin System
- Implement MCPToolPlugin interface
- Auto-discovery by PluginManager
- Register via factory or manually

## ANTI-PATTERNS

- **NO direct PyGithub** → Use infrastructure services
- **NO business logic** → Domain layer only

## Application Components

### AuthenticationMiddleware (`authentication.py` - 602 lines)

API key authentication with SHA-256 hashing and comprehensive security features.

**Key Features:**
- **SHA-256 Hashed API Keys**: Never stored in plaintext
- **Admin API Key**: Support for elevated privileges
- **Brute-Force Protection**: Exponential backoff with lockout
- **Client Lockout**: 5 failures per minute = 60s lockout
- **JWT Token Support**: Parse and expiration checking
- **Runtime API Key Management**: Add/remove keys dynamically
- **Multiple Authentication Headers**: X-API-Key and Authorization Bearer

**Configuration:**
```bash
MCP_AUTH_ENABLED=true
MCP_API_KEYS=key1,key2,key3
MCP_ADMIN_API_KEY=admin_key
MCP_MAX_FAILURES_PER_MINUTE=5
MCP_LOCKOUT_DURATION=60
```

**Thread Safety:**
- Uses `threading.RLock()` for atomic state management
- Thread-safe failure tracking and lockout mechanism

**Security Features:**
- SHA-256 hashing for token storage
- API key format validation (16-256 chars, printable ASCII)
- Suspicious operation detection
- Safe logging with sanitized values

**Methods:**
- `authenticate(api_key)`: Validate API key and return (success, client_id)
- `extract_client_identifier(headers)`: Extract client identifier from headers
- `is_authentication_enabled()`: Check if authentication is enabled
- `get_status()`: Return authentication status and statistics

### RateLimiter (`rate_limiter.py` - 214 lines)

Per-client rate limiting using token bucket algorithm.

**Key Features:**
- **100 requests per minute** per client (configurable)
- **Automatic cleanup** of inactive clients (1 hour TTL)
- **Global rate monitoring** across all clients
- **Thread-safe** with `threading.Lock()`
- **Client-specific rate info** retrieval

**Thread Safety:**
- Uses `threading.Lock()` for all modifications
- Thread-safe cleanup at periodic intervals (5 minutes)

**Algorithm:**
- Token bucket style: Tracks timestamps in sliding window (last 60s)
- Removes timestamps outside of window before counting
- LRU cleanup for expired clients

**Metrics:**
- `get_rate_limit_info(client_id)`: Detailed rate limit status
- `get_current_rate(client_id)`: Current request count
- `get_active_clients_count()`: Number of active clients

### MetricsTracker (`metrics_tracker.py` - 220 lines)

Request metrics tracking with execution time monitoring.

**Key Features:**
- **Request counting**: Total, successful, failed
- **Operation-specific metrics**: Each operation tracked separately
- **Execution time tracking**: Min, max, avg execution time
- **Uptime tracking**: Seconds and human-readable format
- **Success rate calculation**: Percentage-based success rate
- **Request ID generation**: REQ-{timestamp}-{counter} format

**Thread Safety:**
- Uses `threading.Lock()` for atomic operations
- Deep copy of operation metrics to avoid lock contention

**Metrics Structure:**
```python
{
    "uptime_seconds": float,
    "uptime_human": str,
    "total_requests": int,
    "successful_requests": int,
    "failed_requests": int,
    "success_rate": float,
    "operations": {
        "operation_name": {
            "total_requests": int,
            "successful_requests": int,
            "failed_requests": int,
            "success_rate": float,
            "avg_execution_time": float,
            "min_execution_time": float,
            "max_execution_time": float
        }
    }
}
```

### HealthMonitor (`health_monitor.py` - 114 lines)

Server health monitoring with metrics aggregation.

**Key Features:**
- Aggregates metrics from MetricsTracker and RateLimiter
- Health status determination: healthy, degraded, unhealthy
- Status thresholds:
  - **healthy**: Success rate >= 80% AND remaining rate limit > 10%
  - **degraded**: Success rate < 80% OR remaining rate limit <= 10%
  - **unhealthy**: Health check failed or critical errors

**Methods:**
- `check_health()`: Returns comprehensive health data including status, uptime, request counts, rate limit information, and per-operation metrics

### ServerConfiguration (`server_configuration.py` - 157 lines)

Server configuration management and validation.

**Key Features:**
- Logging configuration setup from settings
- Server information retrieval
- MCP instructions generation
- Configuration validation with warnings/errors
- Transport validation (stdio, http, sse, streamable-http)
- Port validation (1-65535 for non-stdio transports)
- GitHub token warning if not configured

**Validation:**
- Returns `ValidationResult` with valid/warnings/errors lists
- Checks transport is one of: stdio, http, sse, streamable-http
- Validates port for non-stdio transports

### PROperationHandler (`pr_operation_handler.py` - 264 lines)

PR operations coordination with repository caching.

**Key Features:**
- PR diff fetching via GitHub API
- Repository caching for efficiency
- URL parsing with regex: `r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"`
- Lazy repository initialization
- Detailed error handling and logging

**Repository Caching:**
- Retrieves cached repository from `RepositoryCacheService`
- Caches repository after successful initialization
- Triggers initialization only when needed

**Not Implemented Methods** (return NotImplementedError):
- `describe_pr()` - Generate PR description
- `approve_pr()` - Generate PR approval message
- `review_pr()` - Generate PR review
- `update_pr_changelog()` - Update PR changelog

## Protocol Interfaces

All protocols defined in `interfaces/protocols.py` (230 lines):

### RateLimiterProtocol
```python
def check_rate_limit(self, identifier: str) -> bool
def increment_rate_limit(self, identifier: str) -> None
def get_rate_limit_info(self) -> Dict[str, Any]
```

### MetricsTrackerProtocol
```python
def track_request(self, operation: str, success: bool, execution_time: float) -> None
def get_metrics_summary(self) -> Dict[str, Any]
def generate_request_id(self) -> str
```

### PROperationHandlerProtocol
```python
async def get_pr_diff(self, pr_url: str) -> Dict[str, Any]
async def describe_pr(self, pr_url: str, commit_messages: str, diff_content: str) -> str
async def approve_pr(self, pr_url: str, commit_messages: str, diff_content: str) -> str
async def review_pr(self, pr_url: str, commit_messages: str, diff_content: str) -> str
async def update_pr_changelog(self, pr_url: str, commit_messages: str, diff_content: str) -> str
```

### HealthMonitorProtocol
```python
def check_health(self) -> Dict[str, Any]
```

### ServerConfigurationProtocol
```python
def setup_logging(self) -> None
def get_server_info(self) -> Dict[str, Any]
def get_mcp_instructions(self) -> str
```

### AuthenticationProtocol
```python
def authenticate(self, api_key: Optional[str]) -> Tuple[bool, Optional[str]]
def extract_client_identifier(self, headers: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]
def is_authentication_enabled(self) -> bool
def get_status(self) -> Dict[str, Any]
```

## Key Components

### FastMCPServer (`mcp_server.py`)

**Primary Responsibilities:**
- FastMCP server initialization and configuration
- Tool registration and exposure via MCP protocol
- GitHub PR URL parsing and validation
- Request orchestration through domain use cases
- Response formatting and error handling
- API key authentication and authorization
- Per-client rate limiting enforcement

**Key Methods:**
- `__init__()`: Server setup, tool registration, logging initialization
- `_parse_pr_url()`: Extracts owner/repo/PR number from GitHub URLs
- `_register_tools()`: Defines `get_pr_diff` MCP tool with authentication
- `_authenticate_request()`: Validates API key when authentication is enabled
- `run()`: Starts server with configured transport (stdio/http/sse)

**Security Features:**
- **API Key Authentication**: Optional SHA-256 hashed token-based authentication
  - Enable via `MCP_AUTH_ENABLED=true` environment variable
  - Configure API keys via `MCP_API_KEYS` (comma-separated)
  - Admin key via `MCP_ADMIN_API_KEY` for elevated privileges
  - Supports X-API-Key and Authorization Bearer headers
- **Per-Client Rate Limiting**: Rate limiting using authenticated client_id or IP address
- **Input Validation**: All inputs validated through `InputValidator` before processing
- **Security Exception Handling**: Catches and logs security exceptions with sanitized values
- **Safe Logging**: All parameters sanitized before logging to prevent log injection

### MCP Tool: `get_pr_diff`

**Input:**
- `pr_url`: Full GitHub PR URL (e.g., "https://github.com/owner/repo/pull/123")
- `api_key` (optional): API key for authentication (when authentication is enabled)

**Output:**
- JSON string containing complete `PRDiff` data via `model_dump_json()`

**Processing Flow:**
1. **Authentication** (if enabled): Validate API key via `AuthenticationMiddleware`
2. Parse and validate GitHub PR URL through `InputValidator`
3. Create GitHubPRDiffRepository instance
4. Execute GetPRDiffUseCase with repository
5. Return serialized PRDiff result

**Security Validations:**
- URL format validation (GitHub PR URL pattern)
- Suspicious pattern detection (command injection, path traversal, SQL injection)
- Repository identifier validation (owner/repo naming conventions)
- PR number validation (positive integer within valid range)

## Configuration Integration

### Transport Configuration
The server supports multiple MCP transport protocols via settings:
- **stdio**: Standard MCP client communication (default)
- **http**: HTTP server mode on configurable host/port
- **sse**: Server-sent events transport
- **streamable-http**: FastMCP streamable HTTP

### Settings Dependencies
- `mcp.transport`: Transport protocol selection
- `mcp.port`: Server port (default: 9102)
- `mcp.host`: Server host (default: "127.0.0.1")
- All GitHub and application settings are passed through to infrastructure layer

## Development Guidelines

### Adding New Tools
When adding MCP tools to server:
1. Define tool function with `@self.mcp.tool()` decorator
2. Add proper docstring with parameter descriptions
3. Use domain use cases for business logic
4. Handle errors gracefully with structured logging
5. Return serialized domain entities via `model_dump_json()`

### URL Pattern Matching
The `_parse_pr_url()` method uses regex to extract GitHub PR components:
```python
pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
```
Extend this pattern if supporting additional URL formats.

### Error Handling Strategy
- Log errors with structured context (PR URL, repo details)
- Security exceptions (`InvalidURLError`, `SuspiciousOperationError`, etc.) are caught and logged safely
- Sanitized error values prevent log injection attacks
- Re-raise exceptions to let FastMCP handle MCP-level error responses
- Include relevant request context in error messages
- Failed security validations tracked in metrics for security monitoring

### Testing Integration Points
When testing application layer:
- Mock GitHubPRDiffRepository for unit tests
- Use FastMCP test client for integration testing
- Test URL parsing edge cases
- Verify proper error propagation and logging

## FastMCP Integration

The server leverages FastMCP's capabilities:
- **Tool Auto-Discovery**: Tools are automatically exposed to MCP clients
- **Type Validation**: Pydantic models provide automatic request/response validation
- **Multiple Transports**: Single codebase supports stdio, HTTP, SSE protocols
- **Built-in Logging**: Structured logging integrates with FastMCP's logging system

### MCP Client Usage Example
```python
# Connect to HTTP transport
async with Client("http://127.0.0.1:9102/mcp") as client:
    result = await client.call_tool("get_pr_diff", {
        "pr_url": "https://github.com/owner/repo/pull/123"
    })
```

## Recent Changes (v0.4.9)

### Plugin System (NEW)
**Purpose**: Modular MCP tool architecture for extensibility and easier maintenance

**Key Files:**
- `interfaces/tool_plugin.py` - MCPToolPlugin interface
- `plugin_manager.py` - Plugin discovery and execution

**Features:**
- Plugin registration with enabled/disabled state management
- Tool execution orchestration through PluginManager
- First plugin: `get_pr_diff_plugin` - Get PR diff as modular tool

**Usage Pattern:**
```python
from prdiffer.application.plugin_manager import PluginManager

manager = PluginManager()
plugin = manager.get_plugin("get_pr_diff")
result = await plugin.execute(pr_url="https://github.com/...")
```

### VCS Provider Integration (NEW)
**Purpose**: Multi-provider support through domain layer VCSProviderRegistry

**Integration Points:**
- PROperationHandler uses VCSProviderRegistry to auto-detect provider
- Supports GitHub and GitLab providers
- Extensible for adding Bitbucket, Gitea, etc.

**Usage in PROperationHandler:**
```python
from prdiffer.domain.vcs_provider_registry import VCSProviderRegistry

registry = VCSProviderRegistry()
provider = registry.get_provider(url=pr_url)
if provider:
    diff = await provider.get_pr_diff()
```

### Dependency Injection Support (NEW)
**Purpose**: Constructor injection for testability and loose coupling

**Key Changes:**
- Application components now accept optional DI parameters
- Factory functions provide backward compatibility
- All components use ServiceContainer or ServiceFactory

**Example:**
```python
from prdiffer.infrastructure.di_container import get_container
from prdiffer.infrastructure.service_factory import get_service_factory

class SomeComponent:
    def __init__(self, container=None, logger=None):
        self._container = container or get_container()
        factory = get_service_factory(logger=logger)
        self._logger = logger or factory.get_logger()
```

### Architecture Improvements
- Clean Architecture compliance verified
- Proper layer separation maintained
- Zero circular dependencies
- All classes accept dependencies for easy mocking

## Related Documentation

- **Domain Layer**: `../domain/CLAUDE.md` - Domain entities, use cases, and interfaces
- **Infrastructure Layer**: `../infrastructure/CLAUDE.md` - Infrastructure implementations
- **Components**: `components/CLAUDE.md` - Application components (auth, rate limiting, metrics, health, configuration, operation handler, plugin manager)
- **Interfaces**: `interfaces/CLAUDE.md` - Application-level protocols (MCPToolPlugin)
- **Services**: `services/CLAUDE.md` - Application-level services
- **Main Package**: `../CLAUDE.md` - Overall architecture and package structure
- **Testing**: `tests/unit/application/CLAUDE.md` - Application layer testing guide

This application layer provides a clean separation between MCP protocol interface and domain business logic, making it easy to modify either external interface or internal processing independently.
