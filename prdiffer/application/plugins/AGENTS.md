# AGENTS.md - Application/Plugins

**Status: reserved empty directory (no Python modules; AGENTS.md only).**

## CURRENT STATE
- There is no plugin package, no plugin manager, and no `MCPToolPlugin` type in tree.
- Production tools are registered with `@mcp.tool()` in `prdiffer/application/tool_registry.py`.
- Tools exposed today: `get_pr_diff`, `approve_pr`, `describe_pr` (+ health tool registration on `FastMCPServer`).

## HOW TO ADD A TOOL (CURRENT PATTERN)
1. Implement handler logic (prefer domain use case + injected services/Protocols).
2. Register in `ToolRegistry.register_tools()` with `@mcp.tool()`.
3. Wire dependencies through `FastMCPServer` / `create_mcp_server()`.
4. For `get_pr_diff`-like tools: document all-or-nothing full-context diffs; incompleteness → `E5020_FULL_DIFF_INCOMPLETE`.
5. Add unit tests under `tests/unit/application/`.

## ANTI-PATTERNS
- Do not describe a plugin system as the production path.
- Do not leave docs pointing at nonexistent plugin modules.
- If a plugin architecture is reintroduced later, define contracts first (domain or real `interfaces` modules), then implementations here.
