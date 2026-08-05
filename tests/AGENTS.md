# AGENTS.md - Tests

pytest suite: unit, integration, performance, root phase/client regression tests.

## OVERVIEW
- **146** Python files under `tests/` (~38K lines)
- **~2515** `test_*` functions across **130** `test_*.py` files
- Package under test: **prdiffer 0.6.0**
- Shared fixtures: `tests/conftest.py` (auto env + singleton reset)
- Largest suite remains under `unit/application/components/` (auth)

## STRUCTURE
```
tests/
├── conftest.py                      # Markers, mocks, sample entities, auto-use env/singletons
├── test_github_client.py            # Root client regression
├── test_cache_hashing.py            # Cache key hashing
├── test_phase{1-4}_improvements.py  # Historical phase regression suites
├── unit/
│   ├── domain/                      # Entities, use cases, errors, registry, cache v2/v1, multi-ref
│   ├── infrastructure/              # GitHub, GitLab (incl. vcs_providers/), cache, utils, DI, security, settings
│   ├── application/                 # Tools, components, webhooks, health
│   └── test_version_consistency.py / test_server_gitlab_composition.py
├── integration/                     # Workflows, security, webhooks, MCP surface, GitLab strict, optional real API
└── performance/                     # Microbenches + full-diff harness + GitLab capacity/deadline
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Domain purity / entities** | `unit/domain/` | E5020, cache identity, session use case, GitLabConfig, multi-ref entities |
| **Retry / CB / cache utils** | `unit/infrastructure/utils/` | Circuit breaker, retry, coalescing, cross-loop executor |
| **GitHub adapters / full-diff** | `unit/infrastructure/github/` | Inventory, typed content, multi-ref batch, ordered processor, session |
| **GitLab strict full-diff** | `unit/infrastructure/vcs_providers/`, `test_gitlab_*.py` | Runtime, session, assembler, ops, content |
| **PR diff service / limits** | `unit/infrastructure/` | `test_pr_diff_service*`, `test_diff_limits`, concurrency defaults |
| **MCP tools / auth** | `unit/application/` | Tool registry (E5020 ToolError JSON), components |
| **Strict MCP surface** | `integration/test_full_diff_mcp_surface.py` | In-process FastMCP |
| **GitLab integration** | `integration/test_gitlab_strict_full_diff.py` | No-network session + cache identity |
| **E2E-ish flows** | `integration/` | Workflow, security, webhooks |
| **Full-diff bench validity** | `performance/test_full_diff_benchmark.py` | Loads `scripts/bench_diff_generation.py` |
| **GitLab capacity/deadline** | `performance/test_gitlab_strict_full_diff.py` | Runtime limiter + E5004 |

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
- Auto-use fixtures: `set_test_environment` (`ENV_FOR_DYNACONF=testing`, dummy tokens), `reset_singletons` (cache/settings/logger).
- GitLab allowlist tests may set `GITLAB_ALLOWED_HOSTS` via monkeypatch.
- Multi-ref tests assert request order, capacity bounds, cache hit/miss identity, and fail-closed operational errors.
- CI: `.github/workflows/pr-quality.yml` runs `ruff check`, `ty check`, `pytest tests` on PRs to `main`/`develop` (`uv sync --frozen --group dev`).

## COMMANDS
```bash
./start-unittest.sh --run
./start-unittest.sh --coverage
./start-unittest.sh --parallel
./start-unittest.sh --file tests/unit/domain/test_exceptions.py
./start-unittest.sh --pattern test_gitlab
uv run pytest tests -v --tb=short
uv run pytest tests -m unit
uv run pytest tests -m "not slow"
uv run pytest tests/unit/infrastructure/vcs_providers/ -v
uv run pytest tests/unit/infrastructure/github/ -k multi_ref -v
```

## ANTI-PATTERNS
- NO live GitHub/GitLab tokens required for unit tests.
- NO putting integration tests under `unit/`.
- NO asserting on third-party SDK internals beyond our wrappers.
- NO multi-second sleeps in unit tests (patch timers / use short delays).
- NO production logic that exists only in tests.
