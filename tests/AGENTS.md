# AGENTS.md - Tests

pytest suite: unit, integration, performance, and phase regression tests.

## OVERVIEW
- **116** Python files under `tests/` (~33K lines)
- **~2300** `test_*` functions
- Markers observed: `unit`, `integration`, `security` (+ `@pytest.mark.asyncio` via pytest-asyncio)
- Shared fixtures: `tests/conftest.py` (auto env + singleton reset)

## STRUCTURE
```
tests/
├── conftest.py                 # Fixtures: mocks, sample entities, auto-use env/singletons
├── unit/
│   ├── domain/                 # Entities, use cases, errors, registry
│   ├── infrastructure/         # GitHub, GitLab, cache, utils, DI, security
│   └── application/            # Tools, components, webhooks, health
├── integration/                # Workflows, security, webhooks, optional real API
├── performance/                # Timing benchmarks
└── test_phase{1-4}_improvements.py  # Historical phase regression suites
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| **Domain purity / entities** | `unit/domain/` |
| **Retry / CB / cache** | `unit/infrastructure/utils/` |
| **GitHub adapters** | `unit/infrastructure/github/` |
| **MCP tools / auth** | `unit/application/` |
| **E2E-ish flows** | `integration/` |

## CONVENTIONS
- Unit tests mock all network I/O.
- Prefer domain interfaces in mocks (`Mock(spec=...)`).
- Async tests: project historically mixes anyio guidance with `@pytest.mark.asyncio` — follow neighboring tests in the same package.
- Auto-use fixtures reset singletons between tests.

## ANTI-PATTERNS
- NO live GitHub/GitLab tokens required for unit tests.
- NO putting integration tests under `unit/`.
- NO asserting on third-party SDK internals beyond our wrappers.
