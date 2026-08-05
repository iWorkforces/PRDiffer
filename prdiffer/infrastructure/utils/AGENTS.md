# AGENTS.md - Infrastructure/Utils

Resilience, parallelism, parsing, and shared utilities (~3.8K lines including subpackages).

## STRUCTURE
```
prdiffer/infrastructure/utils/
├── retry/                      # Unified retry package
├── parallel/                   # AsyncParallelExecutor
├── coalescing/                 # Package copy/impl of coalescing
├── circuit_breaker/            # SHIM → circuit_breaker_core/registry
├── metrics/                    # Performance metrics package
├── circuit_breaker_core.py     # Canonical CircuitBreaker (215)
├── circuit_breaker_registry.py # Global registry (271)
├── coalescing_service.py       # Request coalescing (220)
├── delay_calculator.py         # Backoff + jitter (160)
├── error_classifier.py         # Retryability classification (151)
├── rate_limit_parser.py        # Retry-After / rate headers (183)
├── api_health_tracker.py       # Sliding window health (131)
├── diff_utils.py / diff_limits.py
├── pattern_matcher.py
├── url_parser.py
├── logger_factory.py           # get_logger, LazyLoggerMixin, get_null_logger
├── performance.py              # Metrics (may mirror metrics/)
└── retry_logger.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Retry policy** | `retry/handler.py`, `retry/base.py` | Context-aware (skip file 404s) |
| **CB state machine** | `circuit_breaker_core.py` | Prefer over shim package |
| **Fan-out** | `parallel/executor.py` | anyio |
| **Coalesce** | `coalescing_service.py` | Deduplicate concurrent work |
| **Logger mixin** | `logger_factory.py` | Lazy init |

## CONVENTIONS
- Prefer anyio over asyncio APIs in new code.
- Keep pure helpers free of domain orchestration.
- Document shim vs canonical when flattening modules.

## ANTI-PATTERNS
- NO sleeping without jitter/caps on hot paths.
- NO shared mutable globals without locks.
