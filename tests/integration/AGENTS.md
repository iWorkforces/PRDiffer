# AGENTS.md - Integration Tests

Integration tests with real/mixed dependencies, 7 test files, security + error scenarios + workflows.

## OVERVIEW
Tests verify multi-component interactions and external service behavior (not isolated unit tests).

## STRUCTURE
```
tests/integration/
├── test_security.py           # Injection prevention (731 lines)
├── test_error_scenarios.py    # GitHub API error handling (661 lines)
├── test_complete_workflow.py  # End-to-end MCP→GitHub flow (554 lines)
├── test_real_github_api.py    # Live API tests (skip if no token, 259 lines)
├── test_webhook_invalidation.py # HMAC webhook verification (266 lines)
├── test_metrics_endpoint.py   # Prometheus metrics (77 lines)
└── mcp_server_manual_test.py  # Manual FastMCP client (21 lines)
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| **Add security test** | `test_security.py` | Command/SQL/path injection, validation |
| **Add error scenario** | `test_error_scenarios.py` | Rate limits, network errors, GithubException |
| **Add workflow test** | `test_complete_workflow.py` | MCP request → API response flow |
| **Test live API** | `test_real_github_api.py` | Requires GITHUB_TOKEN env var |
| **Test webhooks** | `test_webhook_invalidation.py` | HMAC signature, cache invalidation |
| **Test metrics** | `test_metrics_endpoint.py` | Prometheus format, operation timing |

## CONVENTIONS

### Integration vs Unit
- **Real dependencies**: Components interact without full mocking (unlike unit tests)
- **Partial mocks**: Infrastructure services mocked, domain logic exercised
- **Live API**: `test_real_github_api.py` makes actual GitHub calls (auto-skip if no token)

### Test Patterns
- **Factory injection**: `create_mcp_server()` with mock fixtures for DI
- **Async execution**: `anyio.run()` for async test invocation (not asyncio)
- **Auto-skip pattern**: `pytestmark = pytest.mark.skipif(not os.getenv("GITHUB_TOKEN"), ...)`
- **HMAC verification**: Webhook tests use `hmac.new()` with sha256 signatures

### Security Test Categories (test_security.py)
- Command injection: semicolon, pipe, backtick, `$(...)` substitution
- Path traversal: `../`, `/etc/`, Windows paths
- SQL injection: `--`, `/*`, SQL keywords
- Expects: `SuspiciousOperationError` or `InvalidURLError`

## ANTI-PATTERNS

- **NO full mocking** → Integration tests need real component interaction
- **NO asyncio.run()** → Use `anyio.run()` for async execution
- **NO hardcoded tokens** → Use `os.getenv("GITHUB_TOKEN")`
- **NO skip missing markers** → Always add `@pytest.mark.integration`
- **NO real API in CI** → Live tests auto-skip without token

## COMMANDS
```bash
pytest -m integration                    # All integration tests
pytest tests/integration/test_security.py -v  # Security tests only
GITHUB_TOKEN=xxx pytest tests/integration/test_real_github_api.py  # Live API
```
