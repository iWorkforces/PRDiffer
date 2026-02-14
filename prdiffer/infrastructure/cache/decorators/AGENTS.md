# AGENTS.md - Cache/Decorators

Method-level caching with @cached_method decorator and CachingMixin.

## OVERVIEW
Decorator-based caching for service methods with TTL, LRU eviction, thread-safe RLock.

## STRUCTURE
```
prdiffer/infrastructure/cache/decorators/
├── decorators.py  # @cached_method, CachingMixin (187 lines)
├── utils.py       # _generate_cache_key, _make_hashable
└── __init__.py    # Exports: cached_method, CachingMixin
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Method caching** | `decorators.py` | @cached_method(ttl, key_prefix) |
| **Caching mixin** | `decorators.py` | CachingMixin base class |
| **Key generation** | `utils.py` | MD5-based key from args/kwargs |

## CONVENTIONS

### CachingMixin Pattern
```python
class CachingMixin:
    '''Provides method-level caching with TTL and LRU eviction'''
    
    def __init__(self):
        self._cache: OrderedDict = OrderedDict()
        self._cache_lock = threading.RLock()
        self._request_count = 0
```

### @cached_method Decorator
```python
@cached_method(ttl=300, key_prefix="pr_diff")
async def get_pr_diff(self, pr_url: str) -> PRDiff:
    # Result cached for 300 seconds
    ...
```

**Requirements:**
- Class MUST inherit from CachingMixin
- Works with both sync and async methods
- Key prefix for cache key namespacing

### Key Generation
- MD5 hash of `{key_prefix}:{method_name}:{args}:{kwargs}`
- `_make_hashable()` converts unhashable types (list, dict) to tuples

### Periodic Eviction
- Every 10 requests triggers `_evict_expired_entries()`
- LRU with `move_to_end()` on access

## ANTI-PATTERNS

- NO @cached_method without CachingMixin inheritance (raises TypeError)
- NO mutable default arguments (breaks cache key generation)
- NO missing TTL (set appropriate value for data freshness)

## Files

- `decorators.py`: @cached_method, CachingMixin
- `utils.py`: Key generation utilities
