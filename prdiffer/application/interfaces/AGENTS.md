# AGENTS.md - Application/Interfaces

Application-level protocol definitions for MCP tools and plugins.

## Guidelines

- Define MCP-specific interfaces (tool plugins, request handlers)
- **Most interfaces belong in domain layer** (Clean Architecture)
- Protocol definitions for FastMCP integration
- Type hints for MCP tool parameters/returns
- **Use only when interface is application-specific** (MCP-related)

## Common Patterns

### MCPToolPlugin Interface
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, runtime_checkable, Protocol

@runtime_checkable
class MCPToolPlugin(ABC):
    '''Plugin interface for modular MCP tools'''
    
    @property
    @abstractmethod
    def name(self) -> str:
        '''Tool name exposed to MCP clients'''
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        '''Tool description for MCP clients'''
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        '''JSON Schema for tool parameters'''
        pass
    
    @abstractmethod
    def enabled(self) -> bool:
        '''Check if plugin is enabled'''
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        '''Execute tool with given parameters (async only)'''
        pass
```

### MCP Request Handler Protocol (Rare)
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MCPRequestHandlerProtocol(Protocol):
    '''Protocol for MCP request handling'''
    
    async def handle_request(self, request: dict) -> dict:
        ...
```

## When to Use

- **MCP-specific interfaces** (tool plugins, MCP request handling)
- **Application orchestration protocols** (FastMCP-specific)
- **Plugin system interfaces** (MCPToolPlugin)

## When NOT to Use

- ❌ Business logic interfaces (use domain/interfaces/)
- ❌ Service contracts (use domain/services/)
- ❌ Repository patterns (use domain/repositories/)
- ❌ Infrastructure contracts (use domain/interfaces/)

## Anti-Patterns

- ❌ Defining business logic interfaces in application
- ❌ Large interfaces (violates interface segregation)
- ❌ Missing ABC/Protocol decorators

## Files

- `tool_plugin.py`: MCPToolPlugin interface
- `__init__.py`: Interface exports
