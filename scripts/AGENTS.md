# SCRIPTS DIRECTORY

**Purpose:** Python utilities for architecture validation, benchmarking, and version-controlled git hooks distribution.

## STRUCTURE
```
scripts/
├── analyze_dependencies.py    # AST-based Clean Architecture violation detector (255 lines)
├── bench_diff_generation.py   # Diff generation benchmarking with mock services (163 lines)
├── setup-git-hooks.sh         # Copies git-hooks/ → .git/hooks/, makes executable
└── git-hooks/
    ├── pre-push               # Enforces type-check + lint before push (59 lines)
    └── README.md              # Hook system documentation
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Check architecture violations** | `analyze_dependencies.py` | Run: `python scripts/analyze_dependencies.py --path prdiffer`, exits 1 on violation |
| **Benchmark diff generation** | `bench_diff_generation.py` | Uses mock GitHubAPIServiceInterface, measures FileProcessor performance |
| **Install git hooks** | `setup-git-hooks.sh` | Run once after clone: `./scripts/setup-git-hooks.sh` |
| **Add new git hook** | `git-hooks/<hook-name>` | Create hook file, run setup script, commit to repo |

## GIT HOOKS DISTRIBUTION (NON-STANDARD)
- **Pattern:** Hooks stored in `scripts/git-hooks/` (version-controlled) → copied to `.git/hooks/` (not tracked)
- **Installation:** Manual via `setup-git-hooks.sh` (not automatic on clone)
- **pre-push enforcement:** Blocks push if `start-type-check.sh` or `start-lint.sh --all` fails
- **Bypass:** `git push --no-verify` (not recommended)
- **Team sync:** Hooks update via git pull + re-run setup script

## COMMANDS
```bash
# Architecture validation
python scripts/analyze_dependencies.py --path prdiffer   # Check violations
python scripts/analyze_dependencies.py --path prdiffer --viz  # Print graph

# Benchmarking
python scripts/bench_diff_generation.py --files 100 --lines 500  # Custom load

# Git hooks
./scripts/setup-git-hooks.sh   # Install hooks
```

## ANTI-PATTERNS
- **NO direct execution of hooks** → Run via git (triggers automatically)
- **NO modifying .git/hooks/ directly** → Edit in `scripts/git-hooks/`, re-run setup
- **NO skipping setup on new clone** → Pre-push won't run until installed
- **NO real GitHub API calls in benchmarks** → `bench_diff_generation.py` uses DummyAPIService mock

## ARCHITECTURE ANALYZER RULES
Enforces Clean Architecture layer violations:
1. Domain → Application: **FORBIDDEN**
2. Domain → Infrastructure: **FORBIDDEN**
3. Application → Infrastructure: **FORBIDDEN** (14 violations currently documented)

Uses AST parsing (`ast.NodeVisitor`) to extract imports, filters to `prdiffer.*` modules only.
