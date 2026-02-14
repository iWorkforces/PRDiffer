# AGENTS.md - Cache/Repository

Repository-specific caching with commit-based invalidation and @with_lock decorator.

## OVERVIEW
RepositoryCacheService for GitHub data with TTL, LRU eviction, thread-safe operations.

## STRUCTURE
```
prdiffer/infrastructure/cache/repository/
├── service.py   # RepositoryCacheService (251 lines)
├── models.py    # CacheEntry dataclass, @with_lock decorator
└── __init__.py  # Exports: RepositoryCacheService, CacheEntry, with_lock
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Repository caching** | `service.py` | get_file_content, invalidate_repository |
| **Cache entry model** | `models.py` | CacheEntry dataclass |
| **Thread safety** | `models.py` | @with_lock decorator |

## CONVENTIONS

### Commit-Based Keys
```python
def _generate_cache_key(self, commit_sha: str, file_path: str) -> str:
    '''MD5 hash of {commit_sha}:{file_path}'''
    key = f'{commit_sha}:{file_path}'
    return hashlib.md5(key.encode()).hexdigest()
```

### @with_lock Decorator
```python
def with_lock(func):
    '''Automatic RLock management on methods'''
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)
    return wrapper
```

### TTL Extension on Access
- `extend_ttl` parameter in `_get_valid_entry()` for fresh data access
- Lazy eviction via `_evict_if_needed()` only called on insert

### Case-Insensitive Keys
- Repository keys: `repo_owner.lower(), repo_name.lower()`

## ANTI-PATTERNS

- NO missing @with_lock on write operations
- NO direct cache access without lock
- NO cache keys without commit_sha (stale data risk)

## Files

- `service.py`: RepositoryCacheService with TTL/LRU
- `models.py`: CacheEntry, @with_lock decorator
