# AGENTS.md - Application Layer

FastMCP server orchestration, plugin system, component DI wiring.

## OVERVIEW
MCP server composition root: tool discovery, plugin registration, cross-cutting components.

## STRUCTURE
```
prdiffer/application/
├── components/         # Auth, rate limiting, metrics, health, PR ops, config (7 files, auth.py 581 lines)
├── plugins/            # MCPToolPlugin implementations (get_pr_diff, approve_pr)
├── interfaces/         # MCP-specific protocols (tool_plugin.py)
├── services/           # Application services (if any)
├── mcp_server.py       # 184-line FastMCP orchestrator
├── tool_registry.py    # 479-line MCP tool registration
└── factory.py          # 87-line DI composition root
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
- **Production uses @mcp.tool()**, plugin system exists but not integrated

### Plugin System (Future)
- Implement `MCPToolPlugin` ABC from `interfaces/tool_plugin.py`
- Properties: name, description, parameters (JSON Schema), enabled, category
- `PluginManager.register_plugin()` for runtime registration
- **Current state:** Exists but not integrated (production uses @mcp.tool() directly)

### Component DI
- All components inject dependencies via constructor
- `factory.py` is composition root - creates and wires everything
- Components expose health checks (health_monitor) and metrics (metrics_tracker)
- Use `infrastructure_factory` for creating infrastructure services
- **Optional DI pattern:** `container=None` with singleton fallbacks for testability

### Error Handling
- Components return structured errors via Pydantic models
- Plugin execution wraps exceptions in MCP-compatible format
- Metrics tracking for all operations

### Request Pipeline
- **Request coalescing** to deduplicate concurrent requests
- **Input validation** via SecurityService (architecture violation - see below)
- **Health endpoints** (/health, /metrics, /webhook)
- **Authentication split:** Token auth in Application, input validation in Infrastructure

## ANTI-PATTERNS

- **NO direct infrastructure calls in components** → Inject via DI (14 violations exist)
- **NO business logic** → Domain layer only (components are orchestration)
- **NO PyGithub in plugins** → Use PRDiffService/PROperationHandler
- **NO static plugin registration** → Use PluginManager or factory
- **NO plugin state mutation** → Plugins should be stateless or manage state internally
- **NO synchronous blocking** → All tool execution must be async

## KNOWN ARCHITECTURE VIOLATIONS (14 Total)

**Problem:** Application layer directly imports Infrastructure modules

**Violations by module:**
- `infrastructure.security.input_validator` → 9 violations
- `infrastructure.request_coalescing` → 4 violations
- `infrastructure.logging.console_logger` → 1 violation

**Affected files:**
```python
# Application → Infrastructure (VIOLATION)
prdiffer/application/health_endpoints.py
prdiffer/application/tool_registry.py
prdiffer/application/factory.py
prdiffer/application/mcp_server.py
prdiffer/application/utils/pr_url_parser.py
prdiffer/application/components/pr_operation_handler.py
prdiffer/application/components/authentication.py
prdiffer/application/factories/application_factory.py
```

**Fix approach (not yet implemented):**
1. Define `SecurityService` and `RequestCoalescingService` interfaces in Domain
2. Inject via DI instead of direct imports
3. Verify with: `python scripts/analyze_dependencies.py --path prdiffer`
