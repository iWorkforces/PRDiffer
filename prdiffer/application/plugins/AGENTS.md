# AGENTS.md - Application/Plugins

**Status: reserved empty directory (no Python modules).**

## CURRENT STATE
- Production tools are registered with `@mcp.tool()` in `prdiffer/application/tool_registry.py`.
- There is no `MCPToolPlugin` implementation package and no plugin manager module in tree.
- Tools exposed today: `get_pr_diff`, `approve_pr`, `describe_pr` (+ health).

## HOW TO ADD A TOOL (CURRENT PATTERN)
1. Implement handler logic (prefer domain use case + injected services).
2. Register in `ToolRegistry.register_tools()` with `@mcp.tool()`.
3. Wire dependencies through `FastMCPServer` / `create_mcp_server()`.
4. Add unit tests under `tests/unit/application/test_tool_registry.py`.

## FUTURE PLUGIN SYSTEM
If a plugin architecture is reintroduced, place interfaces in domain or a real `interfaces` module first, then implementations here — do not leave docs describing nonexistent files.
