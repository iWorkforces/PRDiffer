# AGENTS.md - Infrastructure Unit Tests

Adapters, DI, cache, GitLab/GitHub, security, settings (~16.8K lines, 58 py files).

## STRUCTURE (HIGH LEVEL)
```
tests/unit/infrastructure/
├── github/                 # Client, processor, generator, mappers
├── utils/                  # Retry, CB, cache decorator, parsers
├── cache/                  # Cache store/keys/repository
├── security/               # Detector, sanitizer, helpers
├── logging/                # Exception utils
├── factories/              # InfrastructureFactory
├── test_github_repository.py
├── test_gitlab_*.py
├── test_pr_diff_service*.py
├── test_di_container.py
├── test_settings_*.py
├── test_async_parallel_executor.py
├── test_request_coalescing.py
└── …
```

## CONVENTIONS
- Mock PyGithub / python-gitlab / httpx.
- Prefer anyio-compatible async tests consistent with neighboring files.
- Cover retry classification, rate limits, and circuit breaker transitions when touching resilience code.

## ANTI-PATTERNS
- NO live API calls.
- NO integration-only scenarios that belong under `tests/integration/`.
