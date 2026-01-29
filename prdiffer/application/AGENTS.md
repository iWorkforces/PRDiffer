# AGENTS.md - Application Layer

FastMCP server orchestration, plugin system, component DI wiring.

## OVERVIEW
MCP server composition root: tool discovery, plugin registration, cross-cutting components.

## STRUCTURE
```
prdiffer/application/
├── components/         # Auth, rate limiting, metrics, health, PR ops, config (7 files)
├── plugins/            # MCPToolPlugin implementations (get_pr_diff, approve_pr)
├── interfaces/         # MCP-specific protocols (tool_plugin.py)
├── services/           # Application services (if any)
├── mcp_server.py       # 870-line FastMCP orchestrator
├── plugin_manager.py   # 147-line plugin discovery + execution
└── factory.py          # 192-line DI composition root
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add MCP tool** | `plugins/*.py` | Implement MCPToolPlugin (name, desc, params, execute) |
| **Add component** | `components/*.py` | Constructor DI, health checks, metrics |
| **Register plugin** | `factory.py:register_plugin()` or `plugin_manager.py:register_plugin()` | Manual or factory auto-wiring |
| **Modify DI wiring** | `factory.py:create_mcp_server()` | Composition root, all dependencies flow through here |
| **Server lifecycle** | `mcp_server.py:FastMCPServer` | @mcp.tool() registration, startup/shutdown |

## CONVENTIONS

### FastMCP Integration
- Use `@mcp.tool()` decorator for tool exposure (in plugins or server)
- Return Pydantic models for structured responses
- Async-only tool execution (execute() method)

### Plugin System
- Implement `MCPToolPlugin` ABC from `interfaces/tool_plugin.py`
- Properties: name, description, parameters (JSON Schema), enabled, category
- `PluginManager.register_plugin()` for runtime registration
- Auto-discovery via factory or manual registration in server startup

### Component DI
- All components inject dependencies via constructor
- `factory.py` is composition root - creates and wires everything
- Components expose health checks (health_monitor) and metrics (metrics_tracker)
- Use `infrastructure_factory` for creating infrastructure services

### Error Handling
- Components return structured errors via Pydantic models
- Plugin execution wraps exceptions in MCP-compatible format
- Metrics tracking for all operations

## ANTI-PATTERNS

- **NO direct infrastructure calls in components** → Inject via DI
- **NO business logic** → Domain layer only (components are orchestration)
- **NO PyGithub in plugins** → Use PRDiffService/PROperationHandler
- **NO static plugin registration** → Use PluginManager or factory
- **NO plugin state mutation** → Plugins should be stateless or manage state internally
- **NO synchronous blocking** → All tool execution must be async
