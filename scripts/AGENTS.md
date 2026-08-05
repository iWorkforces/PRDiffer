# AGENTS.md - Scripts

Developer tooling: architecture analysis, benches, git hooks.

## STRUCTURE
```
scripts/
├── analyze_dependencies.py    # Clean Architecture AST analyzer (264)
├── bench_diff_generation.py   # Diff generation microbench (161)
├── setup-git-hooks.sh         # Install versioned hooks (82)
└── git-hooks/
    ├── pre-push               # Runs type-check + lint
    └── README.md
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Layer violations** | `analyze_dependencies.py` | `python3 scripts/analyze_dependencies.py --path prdiffer` |
| **Perf bench** | `bench_diff_generation.py` | Mocked API service, no live GitHub |
| **Install hooks** | `setup-git-hooks.sh` | Copies into `.git/hooks/` |

## CONVENTIONS
- Analyzer forbids Domain→Application, Domain→Infrastructure, Application→Infrastructure (top-level imports).
- Hooks are version-controlled under `scripts/git-hooks/`; re-run setup after pull if hooks change.
- Bypass pre-push only with `--no-verify` (discouraged).

## ANTI-PATTERNS
- NO editing `.git/hooks/` without updating `scripts/git-hooks/`.
- NO real network in benches by default.
