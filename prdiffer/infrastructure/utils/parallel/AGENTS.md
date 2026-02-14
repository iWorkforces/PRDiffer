# AGENTS.md - Utils/Parallel

Anyio-based parallel execution with task groups, timeout protection, batch modes.

## OVERVIEW
AsyncParallelExecutor for concurrent operations with Semaphore, Lock, Event primitives.

## STRUCTURE
```
prdiffer/infrastructure/utils/parallel/
├── executor.py     # AsyncParallelExecutor (449 lines)
├── semaphores.py   # SemaphoreManager, LockManager (69 lines)
├── results.py      # BatchResult dataclass, ErrorStrategy enum
└── __init__.py     # Exports: AsyncParallelExecutor, BatchResult, ErrorStrategy
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Parallel execution** | `executor.py` | execute_batch(), execute_with_progress() |
| **Concurrency control** | `semaphores.py` | SemaphoreManager, LockManager |
| **Result handling** | `results.py` | BatchResult generic dataclass |

## CONVENTIONS

### AsyncParallelExecutor Methods
| Method | Purpose |
|--------|---------|
| `execute_batch()` | Simple batch execution |
| `execute_batch_with_context()` | Batch with shared context |
| `execute_mapped_batch()` | Map function over items |
| `execute_with_progress()` | Progress callback support |
| `execute_batch_detailed()` | Returns BatchResult with metadata |

### OPERATIONAL_EXCEPTIONS
```python
OPERATIONAL_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    OSError,
    # ... 21 total exception types
)
```

### Timeout Protection
```python
async with anyio.fail_after(timeout):
    result = await task()
```

### Progress Tracking
```python
async def execute_with_progress(self, tasks, progress_callback):
    '''Nonlocal completed counter with anyio.Lock'''
    completed = 0
    async with anyio.Lock() as lock:
        completed += 1
        await progress_callback(completed, total)
```

### SemaphoreManager
```python
class SemaphoreManager:
    '''Async context manager for anyio.Semaphore'''
    async def __aenter__(self):
        await self._semaphore.acquire()
    async def __aexit__(self, *args):
        self._semaphore.release()
```

## ANTI-PATTERNS

- NO asyncio primitives → Use anyio.Lock, anyio.Semaphore, anyio.Event
- NO unbounded concurrency → Always use Semaphore for limits
- NO missing timeout → Use anyio.fail_after() for protection
- NO blocking in async → All tasks must be awaitable

## Files

- `executor.py`: AsyncParallelExecutor (449 lines)
- `semaphores.py`: SemaphoreManager, LockManager
- `results.py`: BatchResult, ErrorStrategy
