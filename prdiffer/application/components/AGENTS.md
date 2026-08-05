# AGENTS.md - Application/Components

Cross-cutting MCP components (~1.3K lines). Constructor DI + mixin composition.

## STRUCTURE
```
prdiffer/application/components/
├── authentication.py        # AuthenticationMiddleware (350) + AuthFailureRecord
├── jwt_handler.py           # JWTHandlerMixin (161)
├── api_key_manager.py       # APIKeyManagerMixin (135)
├── rate_limiter.py          # RateLimiter (136)
├── metrics_tracker.py       # MetricsTracker (145)
├── health_monitor.py        # HealthMonitor (99)
├── pr_operation_handler.py  # PROperationHandler (133)
├── server_configuration.py  # ServerConfiguration (118)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **API key / lockout** | `authentication.py`, `api_key_manager.py` | SHA-256 keys, failure window, RLock |
| **JWT metadata** | `jwt_handler.py` | Not primary auth decision surface |
| **Rate limits** | `rate_limiter.py` | Per-client limits, thread-safe |
| **Metrics / health** | `metrics_tracker.py`, `health_monitor.py` | Success rate, degraded thresholds |
| **PR orchestration** | `pr_operation_handler.py` | Coordinates ops for tools |
| **Transport config** | `server_configuration.py` | stdio/http/sse/streamable-http |

## CONVENTIONS
- Mixins for auth concerns; `AuthenticationMiddleware` composes JWT + API key mixins.
- Inject `InputValidatorProtocol` when possible; factory fallback is transitional.
- Sanitize logs (never log raw tokens/API keys).
- Thread safety: `threading.RLock` for sync shared state.

## ANTI-PATTERNS
- NO domain business logic (priority/smells) in components.
- NO trusting JWT without configured verification path for authorization decisions.
- NO unbounded failure-record maps (auth caps tracked clients).
