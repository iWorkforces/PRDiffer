# AGENTS.md - Domain/Services

Service interfaces (ABC) only — 9 ports, ~559 lines. Package 0.6.0.

## STRUCTURE
```
prdiffer/domain/services/
├── cache.py                 # CacheServiceInterface (~100)
├── repository_cache.py      # RepositoryCacheServiceInterface (~107)
├── github_api.py            # GitHubAPIServiceInterface (~78)
├── diff.py                  # DiffServiceInterface (~50)
├── pr_diff_service.py       # PRDiffServiceInterface (~80)
├── pattern_matching.py      # PatternMatchingServiceInterface (~35)
├── retry.py                 # RetryServiceInterface (~17)
├── settings.py              # SettingsServiceInterface (~63; get_github_config / get_gitlab_config)
├── logger.py                # LoggerServiceInterface + LogLevel (~32)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add service port** | New `*.py` ABC here | Implement under infrastructure |
| **PR orchestration port** | `pr_diff_service.py` | High-level diff + commit SHA |
| **Typed file content** | `github_api.py` | `get_file_content` → `FileContentResult` |
| **Commit-based cache** | `cache.py` | get/set with commit SHA; optimistic get |
| **Full-context patches** | `diff.py` | `build_full_file_patch`, `extend_patch` |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `CacheServiceInterface` | ABC | `cache.py` | Commit-keyed PRDiff cache |
| `RepositoryCacheServiceInterface` | ABC | `repository_cache.py` | Cache of repository instances |
| `GitHubAPIServiceInterface` | ABC | `github_api.py` | Repo/PR/content API |
| `DiffServiceInterface` | ABC | `diff.py` | Full-file / extended patches |
| `PRDiffServiceInterface` | ABC | `pr_diff_service.py` | Domain-level PR diff ops |
| `PatternMatchingServiceInterface` | ABC | `pattern_matching.py` | File filter/validation |
| `RetryServiceInterface` | ABC | `retry.py` | Retry with backoff |
| `SettingsServiceInterface` | ABC | `settings.py` | Config access (`get_github_config` / `get_gitlab_config`) |
| `LoggerServiceInterface` | ABC | `logger.py` | Logging contract |
| `LogLevel` | StrEnum | `logger.py` | DEBUG…CRITICAL |

## CONVENTIONS
- Abstract methods only; no default I/O.
- Implementations registered via `InfrastructureFactory`.
- `GitHubAPIServiceInterface.get_file_content` returns `FileContentAvailable | FileContentUnavailable`; operational failures raise (auth, rate limit, transport, retry exhaustion).
- Batch content API returns `dict[str, FileContentResult]`; only available texts should be cached by adapters.

## ANTI-PATTERNS
- NO concrete classes with network/cache logic here.
- NO mapping operational API failures into `FileContentUnavailable`.
- NO SDK types in method signatures.
