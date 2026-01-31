# AGENTS.md - Tests

Unit and integration tests: pytest, 863+ tests, ~70% coverage, anyio-first async.

## OVERVIEW
Comprehensive test suite with pytest, markers, fixtures, generator patterns, and parallel execution.

## STRUCTURE
```
tests/
├── unit/               # Unit tests per layer (55 files)
│   ├── domain/
│   ├── infrastructure/
│   └── application/
├── integration/         # Integration tests (8 files)
├── performance/         # Performance tests (8 files, benchmarking)
├── conftest.py         # Shared fixtures (auto-use for env setup)
└── test_phase_*.py     # 4 phase files (80K+ lines total)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add unit test** | `tests/unit/<layer>/` | Mock external deps |
| **Add integration test** | `tests/integration/` | Real dependencies |
| **Add performance test** | `tests/performance/` | Use `time.perf_counter()` |
| **Shared fixtures** | `conftest.py` | Auto-use for env + singleton reset |
| **Test markers** | pytest.ini | unit, integration, slow, security, thread_safety |

## CONVENTIONS

### Test Markers
- `@pytest.mark.unit` - Unit tests (mocked deps)
- `@pytest.mark.integration` - Integration tests (real deps)
- `@pytest.mark.slow` - Slow tests (excluded by default)
- `@pytest.mark.security` - Security tests (injection, validation)
- `@pytest.mark.thread_safety` - Thread safety tests (RLock, concurrency)

### Async Testing (anyio-first)
- **CRITICAL:** Use `@pytest.mark.anyio` (NOT @pytest.mark.asyncio)
- Use anyio primitives: `anyio.Lock`, `anyio.Semaphore`, `anyio.Event`, `anyio.create_task_group()`
- **NO asyncio in tests** → Project is anyio-first
- Pattern: `anyio.from_thread.run_sync()` for mixed sync/async

### Fixtures
- **Auto-use fixtures** in conftest.py for environment setup and singleton reset
- **Generator fixtures** for test data: `mock_github_file()`, `generate_pr_url()`, `generate_diff_content()`
- **Concurrency fixtures:** `run_concurrently()` with anyio.Semaphore for thread safety tests

### Coverage Goals
- Overall: >80% (current: ~70%)
- Domain: >90%
- Infrastructure: >75%
- Application: >85%

### Performance Testing
- Location: `tests/performance/test_performance.py`
- Use `time.perf_counter()` for benchmarking
- Test retry logic, circuit breaker, parallel execution

### Phase-Based Organization
- 4 phase test files: `test_phase_1.py`, `test_phase_2.py`, etc. (80K+ lines combined)
- Organized by development phase for historical context

## COMMANDS
```bash
./start-unittest.sh --run          # All tests
./start-unittest.sh --coverage     # With coverage (HTML+term)
./start-unittest.sh --parallel     # Parallel execution (CPU count workers)
./start-unittest.sh --file <path>  # Specific file
./start-unittest.sh --pattern <p>  # Match pattern (-k equivalent)
./start-unittest.sh --watch        # Watch mode (pytest-watch)

# Run by marker
pytest -m unit                     # Unit tests only
pytest -m integration              # Integration tests only
pytest -m slow                     # Slow tests
pytest -m security                 # Security tests
pytest -m thread_safety            # Thread safety tests
```

## ANTI-PATTERNS

- **NO production logic in tests** → Tests only
- **NO test dependencies** → Use fixtures, not imports between tests
- **NO asyncio in tests** → Use anyio primitives (project is anyio-first)
- **NO real API calls in unit tests** → Mock all external dependencies
- **NO blocking I/O in async tests** → Use AsyncParallelExecutor patterns
- **NO integration tests in unit/** → Separate integration/ directory
