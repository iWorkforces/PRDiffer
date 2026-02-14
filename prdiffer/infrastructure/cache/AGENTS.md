# AGENTS.md - Infrastructure/Cache

Caching infrastructure with commit-based invalidation, LRU eviction, TTL support.

## STRUCTURE
```
prdiffer/infrastructure/cache/
├── service.py       # CacheService (PR diff caching)
├── store.py         # CacheStore (LRU with TTL eviction)
├── keys.py          # CacheKeyManager (MD5/SHA256 key generation)
├── repository/      # Repository-specific caching
└── decorators/      # @cached_method decorator, CachingMixin
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **General caching** | `service.py` | CacheService with get/set/invalidate |
| **LRU storage** | `store.py` | OrderedDict-based LRU eviction |
| **Key generation** | `keys.py` | MD5/SHA256 hashing for cache keys |
| **Method caching** | `decorators/` | @cached_method decorator, CachingMixin |
| **Repository cache** | `repository/` | Commit-based invalidation for PR data |

## CONVENTIONS

### Key Generation
- **Commit-based keys**: MD5 hash of `{commit_sha}:{file_path}` for precise invalidation
- **Hashed keys**: Configurable MD5 (32 chars) or SHA256 (64 chars) via settings.toml
- **Key mapping**: Store original key for debugging (store_key_mapping = true)

### LRU Eviction
- **OrderedDict**: `move_to_end()` on access for access-time ordering
- **Size limit**: `max_size` parameter (default 1000)
- **TTL support**: `evict_expired()` removes stale entries

### Thread Safety
- **RLock**: All cache operations use threading.RLock
- **@with_lock**: Decorator in repository/ for automatic lock management

## ANTI-PATTERNS

- NO cache without invalidation → Commit-based keys prevent stale data
- NO unbounded cache → Always set max_size
- NO missing TTL → Set appropriate ttl for data freshness
- NO asyncio in cache → Use threading.RLock (sync-only)

## Files

- `service.py`: CacheService for PR diff caching
- `store.py`: CacheStore (LRU with TTL)
- `keys.py`: CacheKeyManager (key hashing)
