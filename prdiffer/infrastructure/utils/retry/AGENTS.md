# AGENTS.md - Retry Package

**Package:** 0.6.2  
Context-aware retry with models and factories (~600 lines).

## STRUCTURE
```
prdiffer/infrastructure/utils/retry/
├── base.py        # BaseUnifiedRetryHandler (339)
├── handler.py     # UnifiedRetryHandler (135); RetryHandler alias
├── models.py      # OperationContext + RETRY_EXCEPTIONS (29)
├── factories.py   # get_retry_handler, get_advanced_retry_handler (93)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Core loop / backoff** | `base.py` | Integrates CB + health tracker |
| **Public handler** | `handler.py` | `UnifiedRetryHandler` / `RetryHandler` |
| **Contexts** | `models.py` | `FILE_CONTENT`, `REPOSITORY_ACCESS`, etc. |
| **Factories** | `factories.py` | Wire advanced vs basic handlers |

## CONVENTIONS
- Integrate with `error_classifier` + `rate_limit_parser` + `delay_calculator`.
- **Do not retry file content 404s** (`OperationContext.FILE_CONTENT`).
- Exponential backoff + jitter; optional adaptive delays.
- Optional circuit breaker / API health tracker composition.
- Cap attempts and adaptive delay; never spin forever.

## ANTI-PATTERNS
- NO blind retry of all exceptions.
- NO infinite retries.
- NO treating permanent 404s for missing file content as transient.
- NO logging secrets when recording retry failures.
