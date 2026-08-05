# AGENTS.md - VCS Providers

**Package:** 0.6.0  
GitHub and GitLab adapters implementing domain VCS/repository ports.

## STRUCTURE
```
prdiffer/infrastructure/vcs_providers/
├── github_repository.py    # GitHubVCSRepository + factory
├── gitlab_repository.py    # GitLabVCSRepository
├── gitlab_models.py        # Diff refs / version / snapshot / record models
├── gitlab_inventory.py     # State/cardinality admission + edit classification
├── gitlab_content.py       # Ref-pinned typed raw content fetch
├── gitlab_diff_generator.py # Ordered full-context FileDiffResponse assembly
├── gitlab_operations.py    # Immutable MR version selection + snapshot
├── gitlab_runtime.py       # Bounded SDK runner + status mapper
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **GitHub adapter** | `github_repository.py` | Wraps `infrastructure/github_repository.GitHubPRDiffRepository` |
| **Primary GitHub PR repo** | `../github_repository.py` | Main implementation (sibling module, not this package) |
| **GitLab adapter** | `gitlab_repository.py` | anyio `to_thread` for blocking python-gitlab |
| **GitLab models** | `gitlab_models.py` | `GitLabDiffSnapshot`, `GitLabDiffRecord`, version/refs |
| **GitLab runtime** | `gitlab_runtime.py` | Shared CapacityLimiter, op-scoped clients, E2006/E2007/E3006/E5021 mapping |
| **GitLab ops** | `gitlab_operations.py` | Pin exact MR diff version matching `diff_refs` |
| **Register provider** | `domain/vcs_provider_registry.py` | `supports_repository(url)` auto-detect |

## CONVENTIONS
- Map provider models → domain entities at the boundary (`FileDiffResponse`, `PRDiff`).
- Use shared retry/security utilities where applicable.
- URL detection must not false-positive across hosts (`github.com` vs `gitlab.com` patterns).
- GitLab renames set `FileDiffResponse.previous_path` from `old_path` when distinct; no retrieval redesign.
- Prefer domain interfaces (`PRDiffRepositoryInterface` / `VCSDiffRepositoryInterface`) for registration.
- **GitLabRuntime**: one process-shared limiter; each `run_blocking` uses a fresh client closed in `finally`; `abandon_on_cancel=True`; inject `max_retries`/`obey_rate_limit` via `http_request` defaults (python-gitlab 8.5 constructor lacks those args).
- Status map: 401→E2006, 403→E2007, 404→context (E4001/E4002/E4003), 429→E3006 (no local re-loop), 5xx→E5021, timeout→E5004, connection→E5019.

## ANTI-PATTERNS
- NO provider-specific types leaking to application tools.
- NO live API calls in unit tests.
- NO sharing SDK client objects across workers.
- NO second 429 retry loop outside SDK policy.
- NO `response_body` / tokens in mapped exception details.
- NO registering providers only in infrastructure without domain registry support.
