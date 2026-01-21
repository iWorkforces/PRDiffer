# CLAUDE.md - Application Layer

This file provides guidance for working with the Application Layer of PRDiffer.

**Current Version:** 0.4.8

## Application Layer Overview

The application layer orchestrates the use cases and provides the external interface via FastMCP. It serves as the entry point for MCP clients and handles tool registration and request processing.

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
- `_register_tools()`: Defines the `get_pr_diff` MCP tool with authentication
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
When adding MCP tools to the server:
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
When testing the application layer:
- Mock the GitHubPRDiffRepository for unit tests
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

This application layer provides a clean separation between the MCP protocol interface and the domain business logic, making it easy to modify either the external interface or internal processing independently.

## Related Documentation

- **Domain Layer**: `../domain/CLAUDE.md` - Domain entities, use cases, and interfaces
- **Infrastructure Layer**: `../infrastructure/CLAUDE.md` - Infrastructure implementations
- **Components**: `components/CLAUDE.md` - Application components (auth, rate limiting, metrics)
- **Main Package**: `../CLAUDE.md` - Overall architecture and package structure
- **Testing**: `tests/unit/application/CLAUDE.md` - Application layer testing guide