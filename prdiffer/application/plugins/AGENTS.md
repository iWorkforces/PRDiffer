# AGENTS.md - Application Plugins

MCP tool plugins (future architecture, not yet integrated in production).

## OVERVIEW
MCPToolPlugin implementations for modular tool development. **Current state:** Plugin system exists but production uses `@mcp.tool()` decorators directly in mcp_server.py.

## STRUCTURE
```
prdiffer/application/plugins/
├── get_pr_diff_plugin.py  # GetPRDiffPlugin (example)
└── *_plugin.py             # Additional plugins (future)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add plugin** | New `*_plugin.py` | Implement MCPToolPlugin interface |
| **Register plugin** | `plugin_manager.py` | Call `register_plugin()` |
| **Current production tools** | `mcp_server.py` | Uses `@mcp.tool()` decorators directly |

## CONVENTIONS

### Plugin Interface (Future)
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class MCPToolPlugin(ABC):
    '''Plugin interface for modular MCP tools (not yet integrated)'''
    
    @property
    @abstractmethod
    def name(self) -> str:
        '''Tool name (e.g., "get_pr_diff")'''
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
    async def execute(self, **kwargs) -> Any:
        '''Async tool execution'''
        pass
```

### Current Production Pattern (@mcp.tool)
```python
from fastmcp import FastMCP

mcp = FastMCP('prdiffer')

@mcp.tool()
async def get_pr_diff(pr_url: str) -> dict:
    '''Get PR diff (production pattern)'''
    # Direct implementation in mcp_server.py
    return {'diff': '...'}
```

### Future Plugin Pattern (Not Yet Used)
```python
class GetPRDiffPlugin(MCPToolPlugin):
    '''Future plugin pattern (exists but not integrated)'''
    
    @property
    def name(self) -> str:
        return 'get_pr_diff'
    
    @property
    def description(self) -> str:
        return 'Get full-file context diff for GitHub PR'
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'pr_url': {'type': 'string', 'description': 'GitHub PR URL'}
            },
            'required': ['pr_url']
        }
    
    async def execute(self, pr_url: str) -> dict:
        # Plugin implementation
        return {}
```

## ANTI-PATTERNS

- ❌ Business logic in plugins (use domain layer)
- ❌ Direct infrastructure calls (use injected services)
- ❌ Stateful plugins (manage state carefully or keep stateless)
- ❌ Synchronous blocking (async only)

## Migration Path (Future)

**Current:** `@mcp.tool()` decorators in `mcp_server.py` (production)  
**Future:** MCPToolPlugin implementations registered via PluginManager  
**Benefit:** Better modularity, testability, and plugin discoverability

## Files

- `get_pr_diff_plugin.py`: Example plugin (not integrated)
- (Future plugins as project grows)
