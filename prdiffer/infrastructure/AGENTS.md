# AGENTS.md - Infrastructure Layer

**Package:** 0.6.0  
External integrations: GitHub/GitLab APIs, cache, security, resilience, DI, settings.

## OVERVIEW
~72 Python files. Implements domain ports; owns I/O and third-party SDKs (PyGithub, python-gitlab, Dynaconf). Clean Architecture outer layer — depends on domain only.

## STRUCTURE
```
prdiffer/infrastructure/
├── cache/                      # CacheService, decorators, repository cache, keys, store
├── factories/                  # InfrastructureFactory (184)
├── github/                     # Full-diff path: client, inventory, file_processor, diff_generator, session
├── interfaces/                 # Empty reserved placeholder
├── logging/                    # ConsoleLogger, exception sanitization
├── security/                   # InputValidator, InjectionDetector, InputSanitizer
├── services/                   # GitHubPRDiffService (527)
├── utils/                      # Retry, CB, parallel, coalescing, diff limits, URL, metrics
├── vcs_providers/              # GitHub + GitLab VCS adapters
├── di_container.py             # ServiceContainer (203)
├── github_repository.py        # GitHubPRDiffRepository (461)
├── github_repository_operations.py  # PR ops (209)
├── github_repository_utils.py  # Filtering/logging helpers (127)
├── service_factory.py          # Convenience factory wrapper (102)
└── settings.py                 # SettingsService Dynaconf + RLock (GitHub + GitLab config)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **DI / singletons** | `di_container.py` | `ServiceContainer`, `get_container()` |
| **Wire services** | `factories/infrastructure_factory.py` | `GitHubConfig` sentinels; parallel flags default **true** |
| **Settings** | `settings.py` → `GitHubConfig` / `GitLabConfig` | 30s provider timeout / 180s request timeout |
| **PR repository** | `github_repository.py` | Main PRDiff repository |
| **Full-diff orchestration** | `services/pr_diff_service.py` | Maps `GeneratedFileDiff` → `FileDiffResponse`, size limits, session path |
| **GitHub API + content** | `github/` | Typed content, inventory, ordered processing |
| **Retry** | `utils/retry/` | base / handler / models / factories |
| **Circuit breaker** | `utils/circuit_breaker_core.py` | Canonical; package path is shim |
| **Parallel I/O** | `utils/parallel/executor.py` | ~608; `execute_indexed_batch` |
| **Coalescing** | `utils/coalescing_service.py` | Deduplicate in-flight requests |
| **Cache** | `cache/service.py`, `cache/cache_decorators.py` | Canonical modules; subpackages are shims |
| **Security** | `security/input_validator.py` | Orchestrates detector + sanitizer |
| **GitLab** | `vcs_providers/gitlab_*.py` | python-gitlab provider |
| **Diff size hard limits** | `utils/diff_limits.py` | Strict rejection (no truncation) |

## CONVENTIONS

### Clean Architecture
- Implement domain interfaces/Protocols; map SDK types → domain entities at the boundary.
- No MCP/tool registration here (application layer).

### Resilience
- Retry + circuit breaker + optional API health tracker.
- **Never retry file-content 404s** (added/removed files).
- Exponential backoff with jitter via `delay_calculator.py`.

### Async
- anyio-first; `AsyncParallelExecutor` for fan-out.
- Request coalescing and PR sessions use anyio primitives (`to_thread`, CapacityLimiter).

### Configuration
- Authoritative GitHub config: `SettingsService.get_github_config()` → frozen `GitHubConfig`.
- Authoritative GitLab config: `SettingsService.get_gitlab_config()` → frozen slotted `GitLabConfig` (`gitlab.*` + shared app/diff/mcp fallbacks).
- Manual settings cache with `RLock` (Dynaconf unhashable → no `@lru_cache`); `clear_cache` drops GitHub and GitLab config caches.
- Parallel performance flags (`parallel_file_fetch_enabled`, `parallel_head_base_fetch_enabled`, `parallel_diff_generation_enabled`) default **true** (bounded by `max_concurrent` / `diff_max_workers`).

### Flattened modules + package shims
Several packages re-export flattened canonical modules for import stability:
- `utils/circuit_breaker/*` → `circuit_breaker_core.py` / `circuit_breaker_registry.py`
- `utils/coalescing/*` → `coalescing_service.py` (package may re-export or mirror)
- `cache/decorators/*` → `cache_decorators.py`
- `cache/repository/*` → `cache_repository.py`

Prefer importing the **canonical flattened module** in new code.

### Full-diff hard fails
- Inventory / admission / content / generation / size failures raise `FullDiffIncompleteError` → **E5020**.
- Unexpected algorithm defects may surface as E5003.

## ANTI-PATTERNS
- NO leaking SDK types (PyGithub/python-gitlab) into domain entities or MCP tools.
- NO `@lru_cache` on Dynaconf-backed settings.
- NO bypassing retry/CB for GitHub rate limits without reason.
- NO logging secrets or raw tokens.
- NO unbounded file downloads / unbounded parallel fan-out against VCS APIs.
- NO truncating full-diff public content — hard-fail via `diff_limits` / E5020.
