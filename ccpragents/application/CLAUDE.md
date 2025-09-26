# CLAUDE.md - Application Layer

This file provides guidance for working with the Application Layer of CCPRAgents.

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

**Key Methods:**
- `__init__()`: Server setup, tool registration, logging initialization
- `_parse_pr_url()`: Extracts owner/repo/PR number from GitHub URLs
- `_register_tools()`: Defines the `get_pr_diff` MCP tool
- `run()`: Starts server with configured transport (stdio/http/sse)

### MCP Tool: `get_pr_diff`

**Input:** 
- `pr_url`: Full GitHub PR URL (e.g., "https://github.com/owner/repo/pull/123")

**Output:**
- JSON string containing complete `PRDiff` data via `model_dump_json()`

**Processing Flow:**
1. Parse and validate GitHub PR URL
2. Create GitHubPRDiffRepository instance
3. Execute GetPRDiffUseCase with repository
4. Return serialized PRDiff result

## Configuration Integration

### Transport Configuration
The server supports multiple MCP transport protocols via settings:
- **stdio**: Standard MCP client communication (default)
- **http**: HTTP server mode on configurable host/port
- **sse**: Server-sent events transport
- **streamable-http**: FastMCP streamable HTTP

### Settings Dependencies
- `mcp.transport`: Transport protocol selection
- `mcp.port`: Server port (default: 9101)  
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
- Re-raise exceptions to let FastMCP handle MCP-level error responses
- Include relevant request context in error messages

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
async with Client("http://127.0.0.1:9101/mcp") as client:
    result = await client.call_tool("get_pr_diff", {
        "pr_url": "https://github.com/owner/repo/pull/123"
    })
```

This application layer provides a clean separation between the MCP protocol interface and the domain business logic, making it easy to modify either the external interface or internal processing independently.