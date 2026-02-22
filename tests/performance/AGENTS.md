# AGENTS.md - Performance Tests

Benchmark tests measuring throughput and latency of critical paths.

## OVERVIEW
Performance benchmarks for validation, caching, authentication, health tracking, security patterns, and concurrency.

## WHERE TO LOOK
| Component | Test Class | Benchmark Target |
|-----------|------------|------------------|
| URL/sanitization | `TestInputValidatorPerformance` | 10K ops < 1-2s |
| Caching mixin | `TestCachingPerformance` | 10K cached calls < 0.1s |
| API key hashing | `TestAuthenticationPerformance` | 10K ops < 0.5s |
| Health score/stats | `TestAPIHealthTrackerPerformance` | 10K ops < 0.5s |
| Pattern matching | `TestSecurityPatternMatchingPerformance` | 40K ops < 2s |
| Request coalescing | `TestConcurrencyPerformance` | 10 concurrent → ~10ms (not 100ms) |
| Memory bounds | `TestMemoryEfficiency` | deque/APIHealthTracker window limits |
| Full pipeline | `TestBenchmark` | 20K ops < 3s |

## CONVENTIONS

### Benchmarking Pattern
```python
# Warm up (JIT, cache priming)
for _ in range(10):
    operation()

# Measure
start = time.perf_counter()
for _ in range(iterations):
    operation()
elapsed = time.perf_counter() - start

# Assert + print for visibility
assert elapsed < threshold, f"Too slow: {elapsed:.3f}s"
print(f"Operation: {iterations} ops in {elapsed:.3f}s ({iterations / elapsed:.0f} ops/sec)")
```

### Thresholds
- URL validation: 10K < 1s
- Sanitization: 30K < 2s  
- Cached calls: 10K < 0.1s
- Hashing: 10K < 0.5s
- Pattern matching: 40K < 2s
- Coalescing: 10 concurrent requests ≈ 1 API call time

### Memory Efficiency
- `deque(maxlen=N)` for bounded collections
- APIHealthTracker `window_size` parameter limits stored calls
- Cache `max_cache_size` enforces LRU eviction

### Async Performance
- Use `anyio.create_task_group()` for concurrent benchmark
- `anyio.run()` wrapper for async test execution
- RequestCoalescingService tested for deduplication efficiency

## ANTI-PATTERNS

- **NO `time.time()`** → Use `time.perf_counter()` (higher resolution)
- **NO warm-up skip** → Always warm up before timing (JIT, caching)
- **NO unbounded collections** → Use maxlen on deque, max_cache_size on caches
- **NO tight loops without ops/sec output** → Print throughput for regression tracking
- **NO ignoring cold start** → Document if test measures warm or cold performance
