# AGENTS.md - Infrastructure/Cache

In-process caching with commit-aware keys, TTL, and repository-scoped caches (~1.1K lines).

## STRUCTURE
```
prdiffer/infrastructure/cache/
├── service.py              # CacheService (340) — primary general cache
├── cache_decorators.py     # CachingMixin, cached_method (248)
├── cache_repository.py     # RepositoryCacheService (259)
├── keys.py                 # Key builders (88)
├── store.py                # Low-level store (77)
├── decorators/             # SHIM → cache_decorators
└── repository/             # SHIM → cache_repository
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **General cache** | `service.py` | `get_cache_service()` |
| **Method caching** | `cache_decorators.py` | Mixin for services |
| **Repo cache** | `cache_repository.py` | PR/repo invalidation |
| **Key format** | `keys.py` | Stable cache key construction |

## CONVENTIONS
- Import canonical modules (`cache.service`, `cache.cache_decorators`, `cache.cache_repository`).
- Shims exist only for backward-compatible import paths.
- Thread-safe access; support invalidation on webhook events.

## ANTI-PATTERNS
- NO unbounded growth without eviction/TTL.
- NO caching secrets or raw auth tokens.
