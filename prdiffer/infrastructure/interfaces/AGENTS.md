# AGENTS.md - Infrastructure/Interfaces

**Package:** 0.6.0  
**Status: empty reserved placeholder directory.**

No Python modules live here today. Domain ports live under:
- `prdiffer/domain/interfaces/`
- `prdiffer/domain/services/`

Infrastructure implements those ports in sibling packages (`github/`, `services/`, `cache/`, `security/`, `vcs_providers/`, etc.). It does **not** define a parallel interfaces package.

## GUIDANCE
- Add new contracts in **domain**, not under this directory.
- Keep this folder only if reserved for future infra-only adapter protocols; prefer domain Protocols.

## ANTI-PATTERNS
- NO duplicating domain interface definitions here.
- NO putting business logic in a placeholder package.
