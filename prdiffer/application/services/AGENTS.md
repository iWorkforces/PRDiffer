# AGENTS.md - Application/Services

**Status: empty placeholder directory (no service modules).**

## CURRENT STATE
- Application orchestration lives in:
  - `tool_registry.py` / `pr_diff_executor.py` (tools)
  - `components/` (auth, rate limit, metrics, health, PR ops)
  - domain `usecases/` (business orchestration)
  - infrastructure `services/pr_diff_service.py` (adapter orchestration)
- Do not add application services that re-implement domain rules.

## GUIDANCE
- Prefer domain use cases for business flow.
- Prefer components for MCP cross-cutting concerns.
- Prefer infrastructure services for VCS/cache/retry wiring.
