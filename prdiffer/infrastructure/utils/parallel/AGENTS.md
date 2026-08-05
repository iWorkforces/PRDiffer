# AGENTS.md - Parallel Execution

anyio-based concurrent execution (~566 lines).

## STRUCTURE
```
prdiffer/infrastructure/utils/parallel/
├── executor.py     # AsyncParallelExecutor (443)
├── results.py      # Result containers (45)
├── semaphores.py   # Concurrency helpers (68)
└── __init__.py
```

## CONVENTIONS
- Use task groups + semaphores for bounded fan-out.
- Prefer this over thread pools for async I/O.
- `get_async_parallel_executor()` / `create_async_parallel_executor()` factories.

## ANTI-PATTERNS
- NO unbounded concurrency against GitHub/GitLab APIs.
- NO mixing blocking SDK calls without to_thread/offload strategy.
