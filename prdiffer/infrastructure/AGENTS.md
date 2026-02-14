# INFRASTRUCTURE KNOWLEDGE BASE

## OVERVIEW
External integrations layer: GitHub API, VCS providers, caching, security, async execution, fault tolerance.

## STRUCTURE
```
prdiffer/infrastructure/
├── utils/           # Resilience patterns, diff utilities, URL parsing
├── github/          # GitHub API client, ETag adapter, diff generator
├── vcs_providers/   # GitHub/GitLab repository implementations
├── security/        # Input validation, injection detection
├── logging/         # Exception handling, console logging
├── factories/       # Infrastructure factory, dependency wiring
├── services/        # PR diff service orchestration
└── *.py             # DI container, cache service, async executor, request coalescing
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Retry logic** | `utils/retry/` package | Split into base.py (408), handler.py (136), models.py, factories.py |
| **Circuit breaker** | `utils/circuit_breaker/core.py` | State machine: CLOSED → OPEN → HALF_OPEN, failure threshold, timeout |
| **Caching** | `cache/` package | Commit-based MD5 invalidation, LRU eviction, TTL support |
| **ETag handling** | `github/etag_adapter.py` | HTTP 304 conditional requests to reduce bandwidth |
| **Async execution** | `utils/parallel/executor.py` | 449-line anyio task groups, Semaphore/Lock/Event primitives |
| **Request coalescing** | `utils/coalescing/` | Deduplicate concurrent requests for same resource |
| **Security** | `security/input_validator.py` | 571-line injection detection: command, path traversal, SQL |
| **GitHub API** | `github/client.py` | 545-line PyGithub wrapper with retry/circuit breaker integration |
| **VCS providers** | `vcs_providers/{github,gitlab}_repository.py` | VCSDiffRepositoryInterface implementations |

## CONVENTIONS

### Fault Tolerance
- **Three-tier resilience**: Retry → Circuit Breaker → API Health Tracker (optional)
- **Never retry 404s for file content** → Added/removed files, not transient errors
- **Retryable status codes**: 403, 429, 500+ (configurable via settings)
- **Exponential backoff**: Base delay + jitter, max cap, attempt limit
- **Circuit breaker**: Opens on N failures, half-open after timeout, close on success

### Async Patterns
- **anyio primitives** > threading for async ops (Semaphore, Lock, Event, create_task_group())
- **AsyncParallelExecutor** > ParallelExecutor for non-blocking calls
- **Dual sync/async APIs**: `method()` and `method_async()` for critical utilities
- **Request coalescing**: Deduplicate in-flight requests using anyio.Lock + dict
- **NO asyncio** → Use anyio throughout (backend-agnostic)

### Caching
- **Commit-based keys**: MD5 hash of {commit_sha + file_path} for precise invalidation
- **Manual caching with RLock** for settings (no @lru_cache due to Dynaconf unhashability)
- **LRU eviction**: Configurable max_entries, TTL per cache entry
- **Cache decorators**: `@cache_result()` for function-level caching with invalidation

### GitHub Integration
- **ETag support**: Store/compare ETags, return cached data on 304, reduce API calls
- **Rate limiting**: Detect 403/429, apply smart retry with backoff
- **API client**: Thin PyGithub wrapper, integrates retry/circuit breaker

### LazyLoggerMixin Pattern
- **66-line mixin** to prevent circular imports in infrastructure services
- `self._logger` property with lazy initialization
- Pattern: `if not hasattr(self, '_logger_instance'): self._logger_instance = LoggerFactory.get_logger(...)`

### Thread Safety
- **anyio.Lock** for async operations (not asyncio.Lock)
- **threading.RLock** for sync operations (double-check locking)
- Manual caching pattern: `_instance = None` + `_lock = threading.RLock()`

## ANTI-PATTERNS

- **NO async/await mixed with blocking I/O** → Use AsyncParallelExecutor for network calls
- **NO direct PyGithub in application** → Wrap in infrastructure services with retry logic
- **NO retry 404s for file content** → Not transient, indicates added/removed files
- **NO @lru_cache on settings** → Use manual caching (Dynaconf objects unhashable)
- **NO empty catch blocks in retry/circuit breaker** → Always log failures, track state
- **NO thread-based async** → Use anyio primitives for backend-agnostic async
- **NO bypassing circuit breaker** → Always go through CircuitBreaker for external APIs
- **NO cache without invalidation** → Commit-based keys prevent stale data
- **NO asyncio in infrastructure** → Use anyio.Lock, anyio.Semaphore, anyio.create_task_group()
- **NO old-style typing** → Project uses `from typing import List` (63 violations, documented deviation)
