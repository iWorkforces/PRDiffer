# AGENTS.md - Infrastructure Layer

**Package:** 0.6.2  
External integrations: GitHub/GitLab APIs, cache, security, resilience, DI, settings.

## OVERVIEW
**80** Python modules. Implements domain ports; owns I/O and third-party SDKs (PyGithub, python-gitlab, Dynaconf). Clean Architecture outer layer — depends on domain only.

## STRUCTURE
```
prdiffer/infrastructure/
├── cache/                      # CacheService, decorators, repository cache, keys, store
├── factories/                  # InfrastructureFactory (~234) — GitHub + GitLab wiring
├── github/                     # Full-diff path: client, inventory, file_processor, diff_generator, session
├── interfaces/                 # Empty reserved placeholder
├── logging/                    # ConsoleLogger, exception sanitization
├── security/                   # InputValidator, InjectionDetector, InputSanitizer
├── services/                   # GitHubPRDiffService (~533)
├── utils/                      # Retry, CB, parallel, coalescing, diff limits, URL, metrics
├── vcs_providers/              # GitHub adapter + full GitLab strict pipeline (gitlab_*.py)
├── di_container.py             # ServiceContainer (~203)
├── github_repository.py        # GitHubPRDiffRepository (~462)
├── github_repository_operations.py  # PR ops
├── github_repository_utils.py  # Filtering/logging helpers
├── service_factory.py          # Convenience factory wrapper
└── settings.py                 # SettingsService Dynaconf + RLock (GitHub + GitLab config) (~446)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **DI / singletons** | `di_container.py` | `ServiceContainer`, `get_container()` |
| **Wire services** | `factories/infrastructure_factory.py` | GitHubConfig + GitLabRuntime/session reader |
| **Settings** | `settings.py` → `GitHubConfig` / `GitLabConfig` | 30s provider / 180s request; `max_total_chars` 600k; host/file env overrides |
| **PR repository (GitHub)** | `github_repository.py` | Main PRDiff repository |
| **Full-diff orchestration (GitHub)** | `services/pr_diff_service.py` | Maps `GeneratedFileDiff` → `FileDiffResponse`, size limits, session path |
| **GitHub API + content** | `github/` | Typed content, multi-ref batch, inventory, ordered processing |
| **GitLab strict full-diff** | `vcs_providers/gitlab_*.py` | Runtime, ops, inventory, content, assembler, session |
| **GitLab approve / describe** | `vcs_providers/gitlab_operations.py`, `gitlab_repository.py` | MR note-then-approve and description update for MCP tools |
| **GitLab URL parse** | `utils/url_parser.py` | Nested NS + custom hosts (`parse_gitlab_merge_request_parts`) |
| **Retry** | `utils/retry/` | base / handler / models / factories |
| **Circuit breaker** | `utils/circuit_breaker_core.py` | Canonical; package path is shim |
| **Parallel I/O** | `utils/parallel/executor.py` | ~598; per-batch semaphore; `execute_indexed_batch` |
| **Coalescing** | `utils/coalescing_service.py` | Deduplicate in-flight requests |
| **Cache** | `cache/service.py`, `cache/cache_decorators.py` | Canonical modules; subpackages are shims |
| **Security** | `security/input_validator.py` | Orchestrates detector + sanitizer; GitHub + GitLab URL validation |
| **Diff size hard limits** | `utils/diff_limits.py` | Strict rejection (no truncation); default aggregate 600k chars |

## CONVENTIONS

### Clean Architecture
- Implement domain interfaces/Protocols; map SDK types → domain entities at the boundary.
- No MCP/tool registration here (application layer).

### Resilience
- Retry + circuit breaker + optional API health tracker.
- **Never retry file-content 404s** (added/removed files).
- Exponential backoff with jitter via `delay_calculator.py`.

### Async
- anyio-first; `AsyncParallelExecutor` for fan-out (fresh semaphore per batch — loop-safe reuse).
- GitHub head/base may use one multi-ref content batch under a single capacity bound.
- Request coalescing and PR sessions use anyio primitives (`to_thread`, CapacityLimiter).
- **GitLabRuntime.run_blocking**: process-shared limiter; per-call `base_url` + `deadline_monotonic`; `abandon_on_cancel=False`; wall-clock deadline check after worker.

### Configuration
- Authoritative GitHub config: `SettingsService.get_github_config()` → frozen `GitHubConfig`.
- Authoritative GitLab config: `SettingsService.get_gitlab_config()` → frozen slotted `GitLabConfig`.
  - Priority for allowlist: `GITLAB_ALLOWED_HOSTS` env (CSV) → `settings.toml` `gitlab.allowed_hosts` → default `gitlab.com`.
  - Priority for file admission: `MAX_FILES_ALLOWED` env → `gitlab.max_files_allowed` / `app.max_files_allowed` → default `50`.
  - Priority for GitHub ignore list: `GITHUB_IGNORE_PATTERNS` env (CSV, replaces) → `settings.toml` `github.ignore_patterns`.
- Manual settings cache with `RLock` (Dynaconf unhashable → no `@lru_cache`); `clear_cache` drops GitHub and GitLab config caches.
- Parallel performance flags default **true** (bounded by `max_concurrent` / `diff_max_workers`).

### Flattened modules + package shims
Several packages re-export flattened canonical modules for import stability:
- `utils/circuit_breaker/*` → `circuit_breaker_core.py` / `circuit_breaker_registry.py`
- `utils/coalescing/*` → `coalescing_service.py`
- `cache/decorators/*` → `cache_decorators.py`
- `cache/repository/*` → `cache_repository.py`

Prefer importing the **canonical flattened module** in new code.

### Full-diff hard fails
- Inventory / admission / content / generation / size failures raise `FullDiffIncompleteError` → **E5020**.
- GitLab: pin exactly one MR diff version matching `diff_refs`; equal-content equal-mode modified is hard E5020.
- Unexpected algorithm defects may surface as E5003.

## ANTI-PATTERNS
- NO leaking SDK types (PyGithub/python-gitlab) into domain entities or MCP tools.
- NO `@lru_cache` on Dynaconf-backed settings.
- NO bypassing retry/CB for GitHub rate limits without reason.
- NO logging secrets or raw tokens.
- NO unbounded file downloads / unbounded parallel fan-out against VCS APIs.
- NO truncating full-diff public content — hard-fail via `diff_limits` / E5020.
- NO shared mutable request deadline/base_url on process-wide `GitLabRuntime`.
- NO open host + token SSRF — always `ensure_host_allowed` before client create.
- NO blocking python-gitlab on the event loop (always `run_blocking` / `to_thread`).
