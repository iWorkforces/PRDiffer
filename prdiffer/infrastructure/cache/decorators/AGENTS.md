# AGENTS.md - Cache Decorators (Shim)

**Package:** 0.6.0  
**Backward-compatibility shim.** Canonical implementation: `prdiffer/infrastructure/cache/cache_decorators.py` (248 lines).

## EXPORTS
- `CachingMixin`
- `cached_method`
- `_generate_cache_key`

## STRUCTURE
```
prdiffer/infrastructure/cache/decorators/
├── __init__.py
├── decorators.py   # re-exports from cache_decorators
└── utils.py        # thin helpers / re-exports if present
```

## GUIDANCE
- New code should import from `prdiffer.infrastructure.cache.cache_decorators`.
- Do not add new logic in this package — update the flattened module.
- Pattern matches other flattened-module + package-shim pairs under infrastructure.

## ANTI-PATTERNS
- NO divergent implementations between shim and canonical module.
