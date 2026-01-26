# AGENTS.md - Tests

Unit and integration tests: pytest, 863+ tests, ~70% coverage.

## OVERVIEW
Comprehensive test suite with pytest, markers, fixtures, and parallel execution.

## STRUCTURE
```
tests/
├── unit/               # Unit tests per module
│   ├── domain/
│   ├── infrastructure/
│   └── application/
├── integration/         # Integration tests
├── conftest.py        # Shared fixtures
└── test_*.py          # Test files
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| **Add unit test** | `tests/unit/<module>/` |
| **Add integration test** | `tests/integration/` |
| **Shared fixtures** | `conftest.py` |
| **Test markers** | pytest.ini |

## CONVENTIONS

- pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.security`, `@pytest.mark.thread_safety`
- Coverage goals: Overall >80%, Domain >90%, Infrastructure >75%, Application >85%
- Async tests: `pytest.mark.asyncio`
- Fixtures in conftest.py

## COMMANDS
```bash
./start-unittest.sh --run          # All tests
./start-unittest.sh --coverage     # With coverage
./start-unittest.sh --parallel     # Parallel execution
./start-unittest.sh --file <path>  # Specific file
./start-unittest.sh --watch        # Watch mode
```

## ANTI-PATTERNS

- **NO production logic in tests** → Tests only
- **NO test dependencies** → Use fixtures
