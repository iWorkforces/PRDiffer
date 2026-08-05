# AGENTS.md - Cache Repository (Shim)

**Backward-compatibility shim.** Canonical implementation: `prdiffer/infrastructure/cache/cache_repository.py`.

## EXPORTS
- `RepositoryCacheService`
- `get_repository_cache_service`

## GUIDANCE
- New code should import from `prdiffer.infrastructure.cache.cache_repository`.
- Models/service re-exports may appear here; keep logic in the flattened module.
