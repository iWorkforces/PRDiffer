# AGENTS.md - Cache Decorators (Shim)

**Backward-compatibility shim.** Canonical implementation: `prdiffer/infrastructure/cache/cache_decorators.py`.

## EXPORTS
- `CachingMixin`
- `cached_method`
- `_generate_cache_key`

## GUIDANCE
- New code should import from `prdiffer.infrastructure.cache.cache_decorators`.
- Do not add new logic in this package — update the flattened module.
