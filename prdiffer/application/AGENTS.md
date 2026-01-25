# AGENTS.md - Application Layer

MCP server implementation, FastMCP components, and orchestration.

## Guidelines

- Import domain interfaces from `prdiffer.domain`
- Import infrastructure implementations from `prdiffer.infrastructure`
- Use FastMCP decorators for tool definitions
- Dependency injection via factory pattern
- Return Pydantic models for MCP responses

## Common Patterns

### MCP Tool Definition
```python
from fastmcp import FastMCP
from prdiffer.application.components import PROperationHandler

mcp = FastMCP("PRDiffer")

@mcp.tool()
def get_pr_diff(pr_url: str) -> dict:
    """Get PR diff with full file context."""
    handler = PROperationHandler()
    return handler.get_diff(pr_url)
```

### Component Pattern
```python
class HealthMonitor:
    def __init__(self, logger: LoggerInterface):
        self._logger = logger
    
    def check_health(self) -> dict:
        pass
```

## Files

- `mcp_server.py`: FastMCP server setup
- `factory.py`: Application factory for dependency injection
- `components/`: MCP components (auth, rate limiting, health, metrics)
