# AGENTS.md - Application Layer

MCP server, FastMCP components, plugin system, orchestration.

## OVERVIEW
FastMCP server setup, MCP tool plugins, component wiring, dependency injection orchestration.

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
