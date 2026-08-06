# AGENTS.md - Infrastructure/Cache

**Package:** 0.6.2  
In-process caching with commit-aware keys, TTL/LRU, and repository-scoped caches.

## STRUCTURE
```
prdiffer/infrastructure/cache/
├── service.py              # CacheService (340) — primary general cache
├── cache_decorators.py     # CachingMixin, cached_method (248)
├── cache_repository.py     # RepositoryCacheService (259)
├── keys.py                 # Key builders / hashing (88)
├── store.py                # Low-level TTL store (77)
├── decorators/             # SHIM → cache_decorators
├── repository/             # SHIM → cache_repository (+ thin models re-export)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **General cache** | `service.py` | `get_cache_service()` singleton |
| **Method caching** | `cache_decorators.py` | Mixin for services (`CachingMixin`, `cached_method`) |
| **Repo / instance cache** | `cache_repository.py` | PR/repo invalidation; `get_repository_cache_service()` |
| **Key format** | `keys.py` | Stable construction + optional hashing |
| **Store eviction** | `store.py` | TTL / size eviction primitives |

## CONVENTIONS
- Import **canonical flattened modules**:
  - `prdiffer.infrastructure.cache.service`
  - `prdiffer.infrastructure.cache.cache_decorators`
  - `prdiffer.infrastructure.cache.cache_repository`
- `decorators/` and `repository/` are **backward-compatibility shims** only — do not add new logic there.
- Thread-safe access; support invalidation on webhook events.
- Commit-aware / repo-scoped keys where applicable (avoid cross-repo collisions).

## ANTI-PATTERNS
- NO unbounded growth without eviction/TTL.
- NO caching secrets or raw auth tokens.
- NO caching unavailable file-content sentinels (see `github/` content cache rules).
- NO new business logic inside shim packages.
