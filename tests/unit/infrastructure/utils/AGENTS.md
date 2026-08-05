# AGENTS.md - Infrastructure Utils Unit Tests

11 test modules, ~4.2K lines.

## STRUCTURE
```
tests/unit/infrastructure/utils/
├── test_circuit_breaker.py                # 675
├── test_retry_handler_comprehensive.py    # 513
├── test_retry_handler.py                  # 199
├── test_cache_decorator.py                # 430
├── test_diff_utils.py                     # 428
├── test_rate_limit_parser.py              # 424
├── test_error_classifier.py               # 396
├── test_pattern_matcher.py                # 333
├── test_delay_calculator.py               # 298
├── test_logger_factory.py                 # 265
└── test_coalescing.py                     # 203
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| **CB state machine** | `test_circuit_breaker.py` | CLOSED → OPEN → HALF_OPEN → CLOSED |
| **Retry + CB integration** | `test_retry_handler*.py` | Context-aware retry |
| **Error classification** | `test_error_classifier.py` | 404 file content not retried |
| **Diff helpers** | `test_diff_utils.py` | Diff generation utilities |
| **Request coalescing** | `test_coalescing.py` | In-flight request sharing |

## CONVENTIONS
- Full CB cycle: CLOSED → OPEN → HALF_OPEN → CLOSED.
- Deterministic backoff: patch randomness / use short delays.
- Assert file-content 404s are not retried.
- Canonical CB lives in `circuit_breaker_core.py`; package `utils/circuit_breaker/` is a re-export shim — tests should still pass against public imports.

## ANTI-PATTERNS
- NO multi-second sleeps in unit tests.
- NO live network or real rate-limit waits.
