# AGENTS.md - Application/Services

**Status: empty placeholder directory (no service modules; AGENTS.md only).**

## CURRENT STATE
- Application orchestration lives in:
  - `tool_registry.py` / `pr_diff_executor.py` (MCP tools + coalesced PR diff execution)
  - `components/` (auth, rate limit, metrics, health, PR ops, server config)
  - domain `usecases/` (business orchestration, e.g. `GetPRDiffUseCase`)
  - infrastructure services (VCS/cache/retry wiring; e.g. PR diff service)
- No application-layer service classes exist under this path.

## GUIDANCE
- Prefer domain use cases for business flow.
- Prefer components for MCP cross-cutting concerns.
- Prefer infrastructure services for VCS/cache/retry wiring.
- Do not add application services that re-implement domain rules (including full-diff completeness / `E5020`).

## ANTI-PATTERNS
- NO inventing service modules here without a clear application-boundary responsibility.
- NO duplicating `ToolRegistry` or domain use-case logic under this package.
