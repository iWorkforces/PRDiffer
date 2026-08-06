# AGENTS.md - Infrastructure/Utils

**Package:** 0.6.2  
Resilience, parallelism, parsing, and shared utilities (including subpackages).

## STRUCTURE
```
prdiffer/infrastructure/utils/
├── retry/                      # Unified retry package (base, handler, models, factories)
├── parallel/                   # AsyncParallelExecutor (~598 in executor.py; per-batch semaphore)
├── coalescing/                 # Package path for coalescing
├── circuit_breaker/            # SHIM → circuit_breaker_core / registry
├── metrics/                    # Performance metrics package
├── circuit_breaker_core.py     # Canonical CircuitBreaker (215)
├── circuit_breaker_registry.py # Global registry (271)
├── coalescing_service.py       # Request coalescing (220)
├── delay_calculator.py         # Backoff + jitter (160)
├── error_classifier.py         # Retryability classification (151)
├── rate_limit_parser.py        # Retry-After / rate headers (183)
├── api_health_tracker.py       # Sliding window health (131)
├── diff_limits.py              # Strict size hard limits (67)
├── diff_utils.py               # DiffServiceInterface impl
├── pattern_matcher.py          # Ignore/extension patterns
├── url_parser.py               # GitHub PR + GitLab MR URL parsing (~281; custom hosts)
├── logger_factory.py           # get_logger helpers, LazyLoggerMixin (123)
├── performance.py              # Metrics (may mirror metrics/)
└── retry_logger.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Retry policy** | `retry/handler.py`, `retry/base.py` | Context-aware (skip file 404s) |
| **CB state machine** | `circuit_breaker_core.py` | Prefer over shim package |
| **Fan-out** | `parallel/executor.py` | anyio task groups + per-batch semaphores |
| **Indexed identity** | `execute_indexed_batch` | Ordered outcomes; strict `IndexedBatchError` |
| **Coalesce** | `coalescing_service.py` | Deduplicate concurrent work |
| **Full-diff size** | `diff_limits.py` | `assert_*` → E5020 RESPONSE_SIZE_LIMIT |
| **GitLab/GitHub URLs** | `url_parser.py` | `parse_github_*`, `parse_gitlab_merge_request_parts` (nested NS + host) |
| **Logger mixin** | `logger_factory.py` | Lazy init / null logger |

## CONVENTIONS
- Prefer anyio over asyncio APIs in new code.
- Keep pure helpers free of domain orchestration.
- Document **shim vs canonical** when flattening modules:
  - Canonical CB: `circuit_breaker_core.py` / `circuit_breaker_registry.py`
  - Package `circuit_breaker/` re-exports only
- Coalescing: prefer consistent imports (`coalescing_service` vs package) within a change set.
- Parallel full-diff work must preserve identity/order via `execute_indexed_batch`.
- Executor creates a fresh semaphore per batch (safe across independent anyio loops).

## ANTI-PATTERNS
- NO sleeping without jitter/caps on hot paths.
- NO shared mutable globals without locks.
- NO blind retry of all exceptions (especially content 404s).
- NO completion-order append for identity-sensitive full-diff batches.
- NO truncating diffs in `diff_limits` helpers — hard-fail only.
