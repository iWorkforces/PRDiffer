# AGENTS.md - Infrastructure Unit Tests

Adapters, DI, cache, GitLab/GitHub, security, settings, full-diff plumbing (~60 test modules).

## STRUCTURE (HIGH LEVEL)
```
tests/unit/infrastructure/
├── github/                              # Client, processor, generator, mappers, session, inventory
├── utils/                               # Retry, CB, cache decorator, parsers
├── cache/                               # Cache store/keys/decorators + repository/
├── security/                            # Detector, sanitizer, helpers
├── logging/                             # Exception utils
├── factories/                           # InfrastructureFactory
├── test_github_repository.py
├── test_gitlab_*.py                     # provider, operations, pagination
├── test_pr_diff_service.py
├── test_pr_diff_service_comprehensive.py
├── test_pr_diff_service_full_context.py # Strict full-context PRDiff mapping
├── test_pr_diff_service_updates.py
├── test_github_config_wiring.py         # GitHubConfig defaults through settings/factory
├── test_full_diff_concurrency_defaults.py  # parallel_* flags default true; capacity bounds
├── test_diff_limits.py                  # Strict size limits (no silent truncate)
├── test_async_parallel_executor.py      # 842 — anyio parallel executor
├── test_di_container.py
├── test_settings_*.py
├── test_request_coalescing.py
├── test_input_validator.py
└── …
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Full-diff config defaults** | `test_github_config_wiring.py`, `test_full_diff_concurrency_defaults.py` | Worker capacity, parallel flags off by default |
| **Strict size limits** | `test_diff_limits.py` | `RESPONSE_SIZE_LIMIT` / E5020 |
| **Service full-context** | `test_pr_diff_service_full_context.py` | Generated full-context → PRDiff |
| **Parallel executor** | `test_async_parallel_executor.py` | anyio task groups, ordered batches |
| **GitHub adapter details** | `github/` | See package AGENTS.md |
| **Resilience** | `utils/` | Retry + circuit breaker |

## CONVENTIONS
- Mock PyGithub / python-gitlab / httpx.
- Prefer anyio-compatible async tests consistent with neighboring files (`@pytest.mark.asyncio` or `@pytest.mark.anyio`).
- Cover retry classification, rate limits, and circuit breaker transitions when touching resilience code.
- Never retry 404s for file content in retry/error-classifier tests.

## ANTI-PATTERNS
- NO live API calls.
- NO integration-only scenarios that belong under `tests/integration/`.
- NO multi-second sleeps (patch delays / short timeouts).
