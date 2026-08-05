# AGENTS.md - Retry Package

Context-aware retry with models and factories (~600 lines).

## STRUCTURE
```
prdiffer/infrastructure/utils/retry/
├── base.py        # BaseUnifiedRetryHandler (339)
├── handler.py     # UnifiedRetryHandler (135)
├── models.py      # Config/models (29)
├── factories.py   # get_retry_handler, get_advanced_retry_handler (93)
└── __init__.py
```

## CONVENTIONS
- Integrate with error classifier + rate limit parser.
- **Do not retry file content 404s.**
- Exponential backoff + jitter via delay calculator.
- Optional circuit breaker / health tracker composition.

## ANTI-PATTERNS
- NO blind retry of all exceptions.
- NO infinite retries.
