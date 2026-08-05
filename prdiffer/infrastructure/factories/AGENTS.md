# AGENTS.md - Infrastructure/Factories

**Package:** 0.6.0  
`InfrastructureFactory` implements domain `InfrastructureFactoryInterface` (184 lines).

## STRUCTURE
```
prdiffer/infrastructure/factories/
├── infrastructure_factory.py  # create_* for all infra services (184)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Wire GitHub stack** | `create_github_api_service`, `create_pr_diff_service` | Reads `GitHubConfig` via `get_settings_service()` |
| **File processor / diffs** | `create_file_processor`, `create_diff_generator` | Parallel thresholds from config |
| **Process-wide factory** | `get_infrastructure_factory()` | Returns new `InfrastructureFactory()` |

## METHODS (HIGH LEVEL)
Settings, logger, cache, repository cache, GitHub API, diff utils, pattern matching, retry, PR diff service, file processor, diff generator, input validator.

## CONVENTIONS
- Prefer **one authoritative `GitHubConfig`** when wiring clients/processors/services (no ad-hoc defaults that diverge from settings).
- Parallel flags from config default **true** (settings + `GitHubConfig`):
  - `parallel_file_fetch_enabled`
  - `parallel_head_base_fetch_enabled`
  - `parallel_diff_generation_enabled`
- When parallel file fetch is disabled, serialized capacity uses `github_worker_capacity` semantics (capacity 1).
- Diff generator receives `parallel_enabled` + `diff_max_workers` / `diff_parallel_threshold` from config.
- Return domain interfaces / concrete adapters as appropriate for callers.
- Lazy-import security validator to avoid circular imports where needed.

## ANTI-PATTERNS
- NO circular imports with application layer (application injects factory results; avoid re-entering carelessly).
- NO hardcoding timeouts/limits that already live on `GitHubConfig`.
- NO unbounded fan-out — always respect `max_concurrent` / `diff_max_workers`.
