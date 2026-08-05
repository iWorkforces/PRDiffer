# AGENTS.md - Infrastructure Utils Unit Tests

11 test modules, ~4.2K lines.

## STRUCTURE
```
tests/unit/infrastructure/utils/
├── test_circuit_breaker.py                # 675
├── test_retry_handler_comprehensive.py    # 513
├── test_retry_handler.py                  # 199
├── test_cache_decorator.py                # 430
├── test_diff_utils.py                     # 426
├── test_rate_limit_parser.py              # 424
├── test_error_classifier.py               # 396
├── test_pattern_matcher.py                # 333
├── test_delay_calculator.py               # 298
├── test_logger_factory.py                 # 265
└── test_coalescing.py                     # 203
```

## CONVENTIONS
- Full CB cycle: CLOSED → OPEN → HALF_OPEN → CLOSED.
- Deterministic backoff: patch randomness / use short delays.
- Assert file-content 404s are not retried.

## ANTI-PATTERNS
- NO multi-second sleeps in unit tests.
