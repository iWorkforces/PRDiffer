# AGENTS.md - Application Component Unit Tests

6 modules, ~3.6K lines.

## STRUCTURE
```
tests/unit/application/components/
├── test_authentication.py         # 1145 — largest suite
├── test_metrics_tracker.py        # 564
├── test_rate_limiter.py           # 521
├── test_pr_operation_handler.py   # 459
├── test_server_configuration.py   # 458
└── test_health_monitor.py         # 408
```

## WHERE TO LOOK
| Task | File |
|------|------|
| JWT / API key / lockout | `test_authentication.py` |
| Rate limit windows | `test_rate_limiter.py` |
| Metrics counters | `test_metrics_tracker.py` |
| Health thresholds | `test_health_monitor.py` |

## CONVENTIONS
- Inject mocks for validators and loggers.
- Cover thread-safety-sensitive paths with concurrent scenarios when modifying locks.

## ANTI-PATTERNS
- NO depending on wall-clock alone for lockout tests without controllable time.
