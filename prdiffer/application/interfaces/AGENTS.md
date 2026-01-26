# AGENTS.md - Application/Interfaces

Application-level protocol definitions.

## Guidelines

- Define MCP-specific interfaces
- Protocol definitions for FastMCP integration
- Type hints for MCP tool parameters/returns

## Common Patterns

### MCP Protocol
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MCPToolInterface(Protocol):
    def invoke(self, **kwargs) -> dict:
        ...
```

## Files

- `__init__.py`: Interface exports
