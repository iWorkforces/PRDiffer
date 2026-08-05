# AGENTS.md - Scripts

Developer tooling: architecture analysis, full-diff benchmarks, git hooks.

## STRUCTURE
```
scripts/
├── analyze_dependencies.py    # Clean Architecture AST analyzer (264)
├── bench_diff_generation.py   # Deterministic strict-v1 full-diff harness
├── setup-git-hooks.sh         # Install versioned hooks (82)
└── git-hooks/
    ├── pre-push               # Runs type-check + lint
    └── README.md
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Layer violations** | `analyze_dependencies.py` | `python3 scripts/analyze_dependencies.py --path prdiffer` |
| **Full-diff baseline/post** | `bench_diff_generation.py` | Matrix `strict-v1`; modes `sync-current`, `async-current-negative-control`, post worker modes |
| **Install hooks** | `setup-git-hooks.sh` | Copies into `.git/hooks/` |

## FULL-DIFF BENCHMARK (`bench_diff_generation.py`)
- **Matrix `strict-v1`** (seed `5020`, 1 warmup excluded from samples):
  - `medium`: 25 files × 200 lines × 5 samples
  - `large`: 250 files × 1000 lines × 5 samples
  - `pathological`: 10 files × 5000 near-matching lines × 3 samples
- **Baseline modes**: `sync-current`, `async-current-negative-control` (records event-loop blocking; does not claim safety)
- **Post modes** (Todo 14+): `serialized-worker-1`, `bounded-worker-2`, `bounded-worker-4` — unsupported until implemented
- **Artifacts**: refuse overwrite by default; sealed baseline under `.omo/evidence/full-diff-correctness-performance/`
- **No network**: in-memory fake repository/content only

```bash
# Capture sealed baseline
uv run python scripts/bench_diff_generation.py \
  --matrix strict-v1 --phase baseline \
  --modes sync-current,async-current-negative-control \
  --json .omo/evidence/full-diff-correctness-performance/task-1-full-diff-correctness-performance.baseline.json

# Compare later post report
uv run python scripts/bench_diff_generation.py \
  --compare <baseline.json> <post.json> --json comparison.json
```

## CONVENTIONS
- Analyzer forbids Domain→Application, Domain→Infrastructure, Application→Infrastructure (top-level imports).
- Hooks are version-controlled under `scripts/git-hooks/`; re-run setup after pull if hooks change.
- Benchmark fixtures must stay deterministic (stable digests across baseline/post).

## ANTI-PATTERNS
- NO editing `.git/hooks/` without updating `scripts/git-hooks/`.
- NO live network in benches.
- NO overwriting a sealed baseline without an intentional new path.
