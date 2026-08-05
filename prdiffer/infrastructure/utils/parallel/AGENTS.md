# AGENTS.md - Parallel Execution

**Package:** 0.6.0  
anyio-based concurrent execution for bounded fan-out.

## STRUCTURE
```
prdiffer/infrastructure/utils/parallel/
├── executor.py     # AsyncParallelExecutor (~608)
├── results.py      # BatchResult, IndexedItemOutcome, IndexedBatchError (~125)
├── semaphores.py   # SemaphoreManager / LockManager (~68)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Executor** | `executor.py` | Task groups + semaphores; factories at bottom |
| **Indexed batch** | `execute_indexed_batch` | Identity-preserving full-diff fan-out |
| **Result types** | `results.py` | `ErrorStrategy`, `IndexedBatchResult`, `IndexedBatchError` |
| **Factories** | `get_async_parallel_executor`, `create_async_parallel_executor` | Singleton vs fresh |

## CONVENTIONS
- Use task groups + semaphores for bounded fan-out.
- Prefer this over thread pools for async I/O; use `anyio.to_thread` for blocking SDKs at the call site.
- **`execute_indexed_batch`**:
  - Outcomes keyed by submission index; returned in **input order**
  - Unique keys required
  - Strict mode cancels siblings and raises `IndexedBatchError` with **full ordered outcomes** — never a compacted success list
  - Prefer this for full-diff content/diff fan-out
- Non-indexed helpers may use completion-order lists with `ErrorStrategy` (IGNORE/RAISE/COLLECT/CONTINUE) — not for identity-sensitive assembly.

## ANTI-PATTERNS
- NO unbounded concurrency against GitHub/GitLab APIs.
- NO mixing blocking SDK calls without `to_thread`/offload strategy.
- NO completion-order append for identity-sensitive full-diff work — use `execute_indexed_batch`.
- NO dropping failed-item identity when strict full-diff completeness is required.
