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
- **Indexed batch API** (`execute_indexed_batch`): outcomes keyed by submission index; returned in input order; unique keys required. Strict mode cancels siblings and raises `IndexedBatchError` with full ordered outcomes — never a compacted success list. Prefer this for full-diff content/diff fan-out.

## ANTI-PATTERNS
- NO unbounded concurrency against GitHub/GitLab APIs.
- NO mixing blocking SDK calls without to_thread/offload strategy.
- NO completion-order append for identity-sensitive full-diff work — use `execute_indexed_batch`.
