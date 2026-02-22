# AGENTS.md - Infrastructure Utils Tests

Unit tests for retry, circuit breaker, caching, rate limiting, and async utilities.

## OVERVIEW
11 test files covering retry with backoff, circuit breaker state machine, cache decorators, delay calculation, error classification, rate limit parsing, pattern matching, diff utilities, and logging.

## STRUCTURE
```
tests/unit/infrastructure/utils/
├── test_circuit_breaker.py          # State machine tests (675 lines)
├── test_retry_handler_comprehensive.py  # Full retry + CB integration (508 lines)
├── test_retry_handler.py            # Basic retry logic (197 lines)
├── test_cache_decorator.py          # CachingMixin, cached_method (479 lines)
├── test_diff_utils.py               # DiffProcessingConfig, chunking (426 lines)
├── test_rate_limit_parser.py        # RateLimitInfo, retry-after parsing (424 lines)
├── test_error_classifier.py         # Error categorization, retry decisions (396 lines)
├── test_delay_calculator.py         # Exponential backoff, jitter (298 lines)
├── test_pattern_matcher.py          # Ignore patterns, extension filtering (333 lines)
├── test_logger_factory.py           # get_logger, get_null_logger (265 lines)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| **Circuit breaker test** | `test_circuit_breaker.py` — state transitions, registry |
| **Retry logic test** | `test_retry_handler_comprehensive.py` — context-aware, health tracking |
| **Cache test** | `test_cache_decorator.py` — TTL, LRU eviction, stats |
| **Rate limit test** | `test_rate_limit_parser.py` — header parsing, delay calculation |
| **Backoff test** | `test_delay_calculator.py` — exponential, jitter, adaptive |

## CONVENTIONS

### Circuit Breaker State Machine Pattern
Test full cycle: `CLOSED → OPEN → HALF_OPEN → CLOSED`
- Record failures until threshold → OPEN
- Wait for timeout → HALF_OPEN via `can_execute()`
- Record success → CLOSED

### Retry Handler Testing
- Use `call_count = [0]` list for mutable counter in closure
- Mock `random.uniform` for deterministic backoff tests
- Test context-aware: file content 404s NOT retried

### Cache Testing
- Test TTL eviction with `expires_at = time.time() - 100`
- Test LRU via `_enforce_size_limit()` with overflow
- Verify stats: `hit_rate = hits / (hits + misses)`

## ANTI-PATTERNS

- **NO asyncio in tests** → Use anyio primitives (project is anyio-first)
- **NO real delays** → Mock `time.sleep`, use short timeouts (0.1s)
- **NO unmocked random** → Patch `random.uniform` for deterministic tests
- **NO partial state cycles** → Test full CLOSED→OPEN→HALF_OPEN→CLOSED cycle
