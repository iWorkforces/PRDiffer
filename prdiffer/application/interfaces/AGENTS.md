# AGENTS.md - Application/Interfaces

**Status: empty placeholder package.**

## CURRENT STATE
- Contains only `__init__.py` (no interface modules).
- Application-facing Protocols live in **`prdiffer/domain/interfaces/protocols.py`**.
- MCP tools are registered in `tool_registry.py`, not via an application-local plugin ABC.

## GUIDANCE
- Prefer adding new ports under `prdiffer/domain/interfaces/` for Clean Architecture purity.
- Only introduce modules here if the contract is truly MCP/application-specific and must not pollute domain.

## ANTI-PATTERNS
- Do not document or invent `MCPToolPlugin` files that are not in the tree.
