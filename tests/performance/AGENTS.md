# AGENTS.md - Performance Tests

Benchmark-style tests for hot paths and the strict-v1 full-diff harness.

## STRUCTURE
```
tests/performance/
├── test_performance.py              # Component microbenchmarks (~345 lines)
└── test_full_diff_benchmark.py      # strict-v1 harness validity + mode markers
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Harness matrix/modes** | `test_full_diff_benchmark.py` | Workload sizes, seed 5020, baseline vs post modes |
| **Fixture digests** | `test_full_diff_benchmark.py` | Determinism + preflight failures |
| **Overwrite refusal** | `test_full_diff_benchmark.py` | Sealed baseline artifacts |
| **Legacy microbenches** | `test_performance.py` | Validator, cache, auth timing |

## CONVENTIONS
- Full-diff harness lives in `scripts/bench_diff_generation.py`; tests load it by path (no `scripts` package required).
- Prefer tiny synthetic workloads inside unit tests; run the full matrix only for sealed baseline/post capture.
- Use deterministic fixtures; never require network.
- Timing thresholds in legacy tests should leave headroom for slower machines.

## ANTI-PATTERNS
- NO hard absolute timings that fail on slower hardware without margin.
- NO overwriting sealed baseline evidence from tests.
- NO claiming event-loop safety from the `async-current-negative-control` mode.
