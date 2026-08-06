# AGENTS.md - Cache Repository (Shim)

**Package:** 0.6.2  
**Backward-compatibility shim.** Canonical implementation: `prdiffer/infrastructure/cache/cache_repository.py` (259 lines).

## EXPORTS
- `RepositoryCacheService`
- `get_repository_cache_service`

## STRUCTURE
```
prdiffer/infrastructure/cache/repository/
├── __init__.py
├── service.py   # re-exports RepositoryCacheService
└── models.py    # thin models / re-exports if present
```

## GUIDANCE
- New code should import from `prdiffer.infrastructure.cache.cache_repository`.
- Models/service files here re-export only; keep logic in the flattened module.
- Pattern matches other flattened-module + package-shim pairs under infrastructure.

## ANTI-PATTERNS
- NO divergent implementations between shim and canonical module.
- NO unbounded repository instance caches without eviction/invalidation hooks.
