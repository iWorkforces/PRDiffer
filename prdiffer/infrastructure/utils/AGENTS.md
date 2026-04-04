# AGENTS.md - Infrastructure/Utils

Utility functions and helpers: retry, circuit breaker, caching, async execution.

## Guidelines

- Pure functions where possible (no side effects)
- **Dual sync/async APIs** for critical utilities
- Reusable across the codebase
- Well-documented with docstrings
- **anyio primitives** for async (not asyncio)

## Common Patterns

### UnifiedRetryHandler (Dual Sync/Async)
```python
from typing import Callable, TypeVar
import anyio

T = TypeVar('T')

class UnifiedRetryHandler:
    '''Context-aware retry with circuit breaker integration (see retry/ package)'''
    
    def retry_sync(
        self,
        func: Callable[[], T],
        max_retries: int = 3,
        delay: float = 1.0,
    ) -> T:
        '''Synchronous retry with exponential backoff'''
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay * (2 ** attempt))
    
    async def retry_async(
        self,
        func: Callable[[], T],
        max_retries: int = 3,
        delay: float = 1.0,
    ) -> T:
        '''Async retry with exponential backoff (anyio.sleep, not asyncio)'''
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await anyio.sleep(delay * (2 ** attempt))
```

### CircuitBreaker (State Machine)
```python
from enum import Enum

class CircuitBreakerState(Enum):
    CLOSED = 'closed'      # Normal operation
    OPEN = 'open'          # Failure threshold reached
    HALF_OPEN = 'half_open'  # Testing recovery

class CircuitBreaker:
    '''State machine: CLOSED → OPEN → HALF_OPEN → CLOSED'''
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
```

### Manual Caching with RLock (Settings Pattern)
```python
import threading

_settings = None
_settings_lock = threading.RLock()

def get_settings():
    '''Manual caching with double-check locking (no @lru_cache)'''
    global _settings
    if _settings is None:
        with _settings_lock:
            if _settings is None:
                _settings = Dynaconf(...)  # Unhashable
    return _settings
```

### AsyncParallelExecutor (anyio Task Groups)
```python
import anyio

class AsyncParallelExecutor:
    '''443-line anyio-based parallel execution'''
    
    async def execute_parallel(self, tasks: list):
        async with anyio.create_task_group() as tg:
            for task in tasks:
                tg.start_soon(task)
```

## Anti-Patterns

- ❌ Using asyncio primitives (use anyio.Lock, anyio.Semaphore, anyio.Event)
- ❌ @lru_cache on Dynaconf settings (use manual RLock pattern)
- ❌ Thread-based async (use anyio.create_task_group())
- ❌ Blocking I/O in async methods (use AsyncParallelExecutor)
- ❌ Retrying 404s for file content (not transient)

## Known Issues

- **github_repository.py (676 lines)** - Largest file, uses composition with extracted components
- **retry/ package refactored** - Previously 848-line monolith, now split into focused modules

## Files

- `retry/`: Retry package (base.py, handler.py, models.py, factories.py)
- `circuit_breaker/`: Circuit breaker package (core.py, registry.py)
- `../cache/`: Caching package (service.py, store.py, repository/, decorators/)
- `diff_utils.py`: Diff processing utilities
- `diff_limits.py`: Diff size limits and validation
- `pattern_matcher.py`: Pattern matching utilities
- `api_health_tracker.py`: API health monitoring
- `logger_factory.py`: LazyLoggerMixin (66-line circular import prevention)
