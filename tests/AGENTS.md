# AGENTS.md - Tests

pytest suite: unit, integration, performance, root phase/client regression tests.

## OVERVIEW
- **~129** Python files under `tests/` (~35K lines)
- **~2390** `test_*` functions
- Package under test: **prdiffer 0.6.0**
- Shared fixtures: `tests/conftest.py` (auto env + singleton reset)
- Largest suite: `unit/application/components/test_authentication.py` (**1145** lines)

## STRUCTURE
```
tests/
├── conftest.py                      # Markers, mocks, sample entities, auto-use env/singletons
├── test_github_client.py            # Root client regression
├── test_cache_hashing.py            # Cache key hashing
├── test_phase{1-4}_improvements.py  # Historical phase regression suites
├── unit/
│   ├── domain/                      # Entities, use cases, errors, registry, cache v2
│   ├── infrastructure/              # GitHub, GitLab, cache, utils, DI, security, settings
│   ├── application/                 # Tools, components, webhooks, health
│   └── test_version_consistency.py
├── integration/                     # Workflows, security, webhooks, MCP surface, optional real API
└── performance/                     # Microbenches + strict-v1 full-diff harness tests
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Domain purity / entities** | `unit/domain/` | E5020, cache v2, session use case |
| **Retry / CB / cache utils** | `unit/infrastructure/utils/` | Circuit breaker, retry, coalescing |
| **GitHub adapters / full-diff** | `unit/infrastructure/github/` | Inventory, typed content, ordered processor, session |
| **PR diff service / limits** | `unit/infrastructure/` | `test_pr_diff_service*`, `test_diff_limits`, concurrency defaults |
| **MCP tools / auth** | `unit/application/` | Tool registry, components (auth 1145) |
| **Strict MCP surface** | `integration/test_full_diff_mcp_surface.py` | 141 lines; in-process FastMCP |
| **E2E-ish flows** | `integration/` | Workflow, security, webhooks |
| **Full-diff bench validity** | `performance/test_full_diff_benchmark.py` | Loads `scripts/bench_diff_generation.py` |

## MARKERS
Registered in `conftest.pytest_configure` (and partially in `pyproject.toml`):
- `unit` — isolated, no external I/O
- `integration` — cross-component / optional external
- `slow` — slow-running
- `security` — security / vulnerability paths
- `thread_safety` — concurrency / lock paths

`pyproject.toml` `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `--strict-markers`, `testpaths = ["tests"]`.

## CONVENTIONS
- Unit tests mock all network I/O (PyGithub, python-gitlab, httpx).
- Prefer domain interfaces in mocks (`Mock(spec=...)`).
- **Async**: production is anyio-first; tests largely use `@pytest.mark.asyncio` (pytest-asyncio). Some modules use `@pytest.mark.anyio`. Follow neighboring tests in the same package.
- Auto-use fixtures: `set_test_environment` (`ENV_FOR_DYNACONF=testing`, dummy `GITHUB_TOKEN`), `reset_singletons` (cache/settings/logger).
- CI: `.github/workflows/pr-quality.yml` runs `ruff check`, `ty check`, `pytest tests` on PRs to `main`/`develop` (`uv sync --frozen --group dev`).

## COMMANDS
```bash
./start-unittest.sh --run
./start-unittest.sh --coverage
./start-unittest.sh --parallel
./start-unittest.sh --file tests/unit/domain/test_exceptions.py
./start-unittest.sh --pattern test_full_diff
uv run pytest tests -v --tb=short
uv run pytest tests -m unit
uv run pytest tests -m "not slow"
```

## ANTI-PATTERNS
- NO live GitHub/GitLab tokens required for unit tests.
- NO putting integration tests under `unit/`.
- NO asserting on third-party SDK internals beyond our wrappers.
- NO multi-second sleeps in unit tests (patch timers / use short delays).
- NO production logic that exists only in tests.
