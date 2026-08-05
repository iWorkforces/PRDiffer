# AGENTS.md - Domain/Services

Service interfaces (ABC) only — 10 modules, ~558 lines.

## STRUCTURE
```
prdiffer/domain/services/
├── cache.py                 # CacheServiceInterface
├── repository_cache.py      # RepositoryCacheServiceInterface
├── github_api.py            # GitHubAPIServiceInterface
├── diff.py                  # DiffServiceInterface
├── pr_diff_service.py       # PRDiffServiceInterface
├── pattern_matching.py      # PatternMatchingServiceInterface
├── retry.py                 # RetryServiceInterface
├── settings.py              # SettingsServiceInterface
├── logger.py                # LoggerServiceInterface
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add service port** | New `*.py` ABC here | Implement under infrastructure |
| **PR orchestration port** | `pr_diff_service.py` | High-level diff fetch |

## CONVENTIONS
- Abstract methods only; no default I/O.
- Implementations registered via `InfrastructureFactory`.

## ANTI-PATTERNS
- NO concrete classes with network/cache logic here.
