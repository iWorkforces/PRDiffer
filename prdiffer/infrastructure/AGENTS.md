# AGENTS.md - Infrastructure Layer

External integrations: GitHub/GitLab APIs, cache, security, resilience, DI, settings.

## OVERVIEW
72 Python files (~10.1K lines). Implements domain ports; owns I/O and third-party SDKs.

## STRUCTURE
```
prdiffer/infrastructure/
├── cache/                 # CacheService, decorators, repository cache, keys, store
├── github/                # API client, file processor, diff generator, ETag, mappers
├── vcs_providers/         # GitHub + GitLab VCS adapters
├── security/              # InputValidator, InjectionDetector, InputSanitizer
├── logging/               # ConsoleLogger, exception utils
├── services/              # GitHubPRDiffService (408)
├── factories/             # InfrastructureFactory (179)
├── utils/                 # Retry, CB, parallel, coalescing, diff, URL, metrics
├── interfaces/            # Empty placeholder
├── github_repository.py   # GitHubPRDiffRepository (457)
├── github_repository_operations.py / _utils.py
├── di_container.py        # ServiceContainer (203)
├── service_factory.py     # Convenience factory wrapper
└── settings.py            # SettingsService (Dynaconf + RLock cache)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Retry** | `utils/retry/` | base/handler/models/factories |
| **Circuit breaker** | `utils/circuit_breaker_core.py` | Canonical; package path is shim |
| **Parallel I/O** | `utils/parallel/executor.py` | anyio task groups (443) |
| **Coalescing** | `utils/coalescing_service.py` (+ package) | Deduplicate in-flight requests |
| **Cache** | `cache/service.py`, `cache/cache_decorators.py` | TTL/LRU/commit keys |
| **Security** | `security/input_validator.py` | Orchestrates detector + sanitizer |
| **GitHub client** | `github/client.py` + `client_operations.py` | PyGithub wrapper |
| **GitLab** | `vcs_providers/gitlab_*.py` | python-gitlab based provider |
| **DI** | `di_container.py`, `factories/infrastructure_factory.py` | Wire from `SettingsService.get_github_config()` |
| **Authoritative config** | `settings.py` → `GitHubConfig` | 30s GitHub / 180s request timeouts; parallel flags default false |

## CONVENTIONS

### Resilience
- Retry + circuit breaker + optional API health tracker.
- **Never retry file-content 404s** (added/removed files).
- Exponential backoff with jitter via `delay_calculator.py`.

### Async
- anyio-first; `AsyncParallelExecutor` for fan-out.
- Request coalescing uses anyio primitives.

### Caching
- Commit-aware keys where applicable; manual settings cache with RLock.
- Prefer canonical modules under `cache/` (see package shims note).

### Shims
Several packages re-export flattened modules for import stability:
- `utils/circuit_breaker/*` → `circuit_breaker_core.py` / `circuit_breaker_registry.py`
- `cache/decorators/*` → `cache_decorators.py`
- `cache/repository/*` → `cache_repository.py`

## ANTI-PATTERNS
- NO leaking SDK types into domain entities.
- NO `@lru_cache` on Dynaconf-backed settings.
- NO bypassing retry/CB for GitHub rate limits without reason.
- NO logging secrets.
