# AGENTS.md - Application Layer

FastMCP server orchestration, tool registration, and cross-cutting components.

## OVERVIEW
21 Python files (~2.6K lines). Composition root wires tools, health, webhooks, and auth.

## STRUCTURE
```
prdiffer/application/
├── components/           # Auth (split), rate limit, metrics, health, PR ops, config (9 modules)
├── factories/            # ApplicationFactory (98 lines)
├── utils/                # pr_url_parser (88 lines)
├── interfaces/           # Placeholder (empty package)
├── plugins/              # Placeholder (no plugin modules)
├── services/             # Placeholder (no modules)
├── mcp_server.py         # FastMCPServer (189)
├── tool_registry.py      # ToolRegistry (477) — get_pr_diff, approve_pr, describe_pr
├── pr_diff_executor.py   # Coalesced PR diff execution mixin (60)
├── health_endpoints.py   # HealthEndpoints (120)
├── webhook_handler.py    # WebhookHandler (171)
└── factory.py            # create_mcp_server() composition root (87)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add MCP tool** | `tool_registry.py` | `@mcp.tool()` inside `register_tools()` |
| **Add component** | `components/*.py` | Constructor DI + Protocols |
| **Wire server** | `factory.py` | `create_mcp_server()` |
| **Lifecycle** | `mcp_server.py` | Register tools, health, webhooks |
| **URL parse** | `utils/pr_url_parser.py` | Owner/repo/number extraction |

## CONVENTIONS

### FastMCP
- Production tools: **`@mcp.tool()` in `ToolRegistry`**, not a separate plugin package.
- Tools: `get_pr_diff`, `approve_pr`, `describe_pr` (+ health tool on server).
- Async handlers; structured domain entities as return types where applicable.

### Components
- Optional DI with factory fallbacks for tests.
- Auth split across `authentication.py`, `jwt_handler.py`, `api_key_manager.py` mixins.
- Prefer domain Protocols (`interfaces/protocols.py`) in type hints.

### Request pipeline
- Auth → rate limit → validate/sanitize → coalesce → execute → metrics.
- Webhooks invalidate repository/diff caches on relevant GitHub events.

## ARCHITECTURE NOTES
- Analyzer reports **1** top-level Application → Infrastructure import (`factory.py` → infrastructure factory).
- Several components still lazy-import `get_infrastructure_factory()` for default validators/services — treat as transitional; prefer injected ports.

## ANTI-PATTERNS
- NO business rules that belong in domain entities/use cases.
- NO PyGithub/python-gitlab in this layer.
- NO new modules under empty `plugins/` without a real plugin interface plan.
- NO blocking I/O in tool handlers.
