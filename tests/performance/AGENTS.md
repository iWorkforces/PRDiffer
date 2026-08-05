# AGENTS.md - Performance Tests

Benchmark-style tests for hot paths.

## STRUCTURE
```
tests/performance/
└── test_performance.py   # ~345 lines — timing with time.perf_counter()
```

## CONVENTIONS
- Use deterministic fixtures; avoid network.
- Record relative thresholds carefully (flaky on loaded CI machines).
- For microbenchmarks of diff generation, also see `scripts/bench_diff_generation.py`.

## ANTI-PATTERNS
- NO hard absolute timings that fail on slower hardware without margin.
