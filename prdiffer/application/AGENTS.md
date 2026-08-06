# AGENTS.md - Application Layer

FastMCP server orchestration, tool registration, and cross-cutting components.

## OVERVIEW
**21** Python modules. Package **0.6.2**. Composition root wires tools, health, webhooks, and auth.

## STRUCTURE
```
prdiffer/application/
├── components/           # Auth (split), rate limit, metrics, health, PR ops, config (8 modules)
├── factories/            # ApplicationFactory (~98)
├── utils/                # pr_url_parser (~102) — parse_pr_url, parse_pr_target, PRTarget
├── interfaces/           # Placeholder (__init__.py only)
├── plugins/              # Placeholder (AGENTS.md only; no Python)
├── services/             # Placeholder (AGENTS.md only; no Python)
├── mcp_server.py         # FastMCPServer (~194)
├── tool_registry.py      # ToolRegistry (~562) — get_pr_diff / approve_pr / describe_pr (GitHub+GitLab)
├── pr_diff_executor.py   # Coalesced PR diff execution (~84); host-aware coalesce key
├── health_endpoints.py   # HealthEndpoints (~120) — health MCP tool
├── webhook_handler.py    # WebhookHandler (~171)
└── factory.py            # create_mcp_server() (~103); wires gitlab_reader + auto gitlab_pr_operations
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add MCP tool** | `tool_registry.py` | `@mcp.tool()` inside `ToolRegistry.register_tools()` |
| **Add component** | `components/*.py` | Constructor DI + domain Protocols |
| **Wire server** | `factory.py` | `create_mcp_server()` |
| **Lifecycle / transport** | `mcp_server.py` | Register tools, health tool, `/metrics`, `/webhook`; run stdio/http/sse/streamable-http |
| **PR diff coalesce** | `pr_diff_executor.py` | Mixin used by `ToolRegistry`; `GetPRDiffUseCase` + request coalescing |
| **URL parse** | `utils/pr_url_parser.py` | `parse_pr_url` (GitHub only), `parse_pr_target` (GitHub/GitLab + `base_url`) |

## CONVENTIONS

### FastMCP tools
- Production tools live in **`ToolRegistry.register_tools()`** via `@mcp.tool()` — not under `plugins/`.
- **Inventory** (all accept GitHub PR + GitLab MR URLs except `health`):
  | Tool | Purpose | Provider-aware |
  |------|---------|----------------|
  | `get_pr_diff` | Strict full-context diff | Yes |
  | `approve_pr` | Approve + non-empty compliment | Yes |
  | `describe_pr` | Update description body | Yes |
  | `health` | Health/metrics (via `HealthEndpoints`) | No |
- Routing for VCS tools: `parse_pr_target` → GitHub repository class or injected `GitLabPROperationsProtocol` (`base_url` for custom hosts).
- Composition: `create_mcp_server` may promote dual-role `gitlab_reader` to `gitlab_pr_operations` when ops are not passed explicitly (`_is_gitlab_pr_operations` TypeGuard).
- Empty/whitespace-only compliment or description → `ValidationError` (E1001) after `.strip()` without provider calls.
- Failure metrics/logs use the real tool name via `operation=` on security/validation/runtime handlers.
- GitLab domain failures (E2006/E2007/E3006/E4001–E4003/E5021/E5004/E5019) bubble with original codes; unmapped `RuntimeError` (e.g. ops not configured) remaps to provider-neutral safe message + E5002.
- Custom routes: `GET /metrics`, `POST /webhook`.
- Async handlers; structured domain entities (`PRDiff`) as return types where applicable.

### Strict full-diff (`get_pr_diff`)
- **All-or-nothing full-context diffs**: successful responses include every selected file with path/status/stats and **generated full-context** unified `diff` text (not hunk-only provider patches).
- On incomplete reconstruction the tool fails with **`E5020_FULL_DIFF_INCOMPLETE`** and a stable `reason` — never a partial `files` array.
- At the FastMCP boundary, `FullDiffIncompleteError` becomes `ToolError` with compact JSON `{"error_code","message","details"}` (safe details only; no `files`).
- Routing: `parse_pr_target` → GitHub or GitLab (`base_url` forwarded into use case / session for custom hosts).

### Components
- Optional constructor DI with factory fallbacks for tests.
- Auth split: `authentication.py` + `jwt_handler.py` + `api_key_manager.py` mixins.
- Prefer domain Protocols (`prdiffer/domain/interfaces/protocols.py`, `input_validation`, `request_coalescing`) in type hints.

### Request pipeline
- Auth → rate limit → validate/sanitize → coalesce → execute → metrics.
- Coalesce keys include `base_url` for GitLab multi-host correctness.
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
- NO using `parse_pr_url` for GitLab (use `parse_pr_target`).
- NO hard-coding GitHub-only URL validation on `approve_pr` / `describe_pr` (provider dispatch required).
