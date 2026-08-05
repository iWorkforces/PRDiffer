# AGENTS.md - Application Layer

FastMCP server orchestration, tool registration, and cross-cutting components.

## OVERVIEW
21 Python files (~2.6K lines). Package **0.6.0**. Composition root wires tools, health, webhooks, and auth.

## STRUCTURE
```
prdiffer/application/
├── components/           # Auth (split), rate limit, metrics, health, PR ops, config (8 modules)
├── factories/            # ApplicationFactory (98)
├── utils/                # pr_url_parser (87)
├── interfaces/           # Placeholder (__init__.py only)
├── plugins/              # Placeholder (AGENTS.md only; no Python)
├── services/             # Placeholder (AGENTS.md only; no Python)
├── mcp_server.py         # FastMCPServer (191)
├── tool_registry.py      # ToolRegistry (481) — get_pr_diff (FullDiffIncompleteError → ToolError JSON E5020), approve_pr, describe_pr
├── pr_diff_executor.py   # _CoalescedPRDiffExecutionMixin (76)
├── health_endpoints.py   # HealthEndpoints (120)
├── webhook_handler.py    # WebhookHandler (171)
└── factory.py            # create_mcp_server() composition root (87)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add MCP tool** | `tool_registry.py` | `@mcp.tool()` inside `ToolRegistry.register_tools()` |
| **Add component** | `components/*.py` | Constructor DI + domain Protocols |
| **Wire server** | `factory.py` | `create_mcp_server()` |
| **Lifecycle / transport** | `mcp_server.py` | Register tools, health tool, `/metrics`, `/webhook`; run stdio/http/sse/streamable-http |
| **PR diff coalesce** | `pr_diff_executor.py` | Mixin used by `ToolRegistry`; `GetPRDiffUseCase` + request coalescing |
| **URL parse** | `utils/pr_url_parser.py` | `parse_pr_url` (GitHub), `parse_pr_target` (GitHub/GitLab) |

## CONVENTIONS

### FastMCP tools
- Production tools live in **`ToolRegistry.register_tools()`** via `@mcp.tool()` — not under `plugins/`.
- Tools: `get_pr_diff`, `approve_pr`, `describe_pr`.
- Health is registered separately: `HealthEndpoints.get_health_handler()` → `mcp.tool()` on the server.
- Custom routes: `GET /metrics`, `POST /webhook`.
- Async handlers; structured domain entities (`PRDiff`) as return types where applicable.

### Strict full-diff (`get_pr_diff`)
- **All-or-nothing full-context diffs**: successful responses include every selected file with path/status/stats and **generated full-context** unified `diff` text (not hunk-only provider patches).
- On incomplete reconstruction (inventory truncation, limits, binary/oversized, generation failure, etc.) the tool fails with **`E5020_FULL_DIFF_INCOMPLETE`** and a stable `reason` — never a partial `files` array.
- At the FastMCP boundary, `FullDiffIncompleteError` becomes `ToolError` with compact JSON `{"error_code","message","details"}` (safe details only; no `files`).

### Components
- Optional constructor DI with factory fallbacks for tests.
- Auth split: `authentication.py` + `jwt_handler.py` + `api_key_manager.py` mixins.
- Prefer domain Protocols (`prdiffer/domain/interfaces/protocols.py`, `input_validation`, `request_coalescing`) in type hints.

### Request pipeline
- Auth → rate limit → validate/sanitize → coalesce → execute → metrics.
- Webhooks invalidate repository/diff caches on relevant GitHub events (HMAC-verified).

## ARCHITECTURE NOTES
- Analyzer reports **1** top-level Application → Infrastructure import: `factory.py` → `infrastructure.factories.infrastructure_factory`.
- Several modules still lazy-import `get_infrastructure_factory()` / coalescing service for default validators — transitional; prefer injected ports.

## ANTI-PATTERNS
- NO business rules that belong in domain entities/use cases.
- NO PyGithub/python-gitlab in this layer.
- NO production tool registration under empty `plugins/` (use `ToolRegistry`).
- NO inventing application service/plugin modules that are not in the tree.
- NO blocking I/O in tool handlers.
- NO returning partial PR diffs; incompleteness must surface as `E5020`.
