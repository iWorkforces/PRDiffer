# AGENTS.md - VCS Providers

**Package:** 0.6.0  
GitHub and GitLab adapters implementing domain VCS/repository ports. GitLab owns the full strict full-diff pipeline.

## STRUCTURE
```
prdiffer/infrastructure/vcs_providers/
├── github_repository.py     # GitHubVCSRepository + factory (~147)
├── gitlab_repository.py     # GitLabVCSRepository session adapter (~149)
├── gitlab_models.py         # Diff refs / version / snapshot / record models (~163)
├── gitlab_inventory.py      # State/cardinality admission + edit classification (~148)
├── gitlab_content.py        # Ref-pinned typed raw content fetch (~281)
├── gitlab_diff_generator.py # Ordered full-context FileDiffResponse assembly (~149)
├── gitlab_diff_session.py   # Request-scoped session + SessionPRDiffReader (~222)
├── gitlab_operations.py     # Immutable MR version selection (`select_with_client`) (~255)
├── gitlab_runtime.py        # Bounded SDK runner + status mapper (~367)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **GitHub adapter** | `github_repository.py` | Wraps `infrastructure/github_repository.GitHubPRDiffRepository` |
| **Primary GitHub PR repo** | `../github_repository.py` | Main implementation (sibling module, not this package) |
| **GitLab adapter** | `gitlab_repository.py` | Session-capable VCS contract over strict reader |
| **GitLab models** | `gitlab_models.py` | `GitLabDiffSnapshot`, `GitLabDiffRecord`, version/refs |
| **GitLab inventory** | `gitlab_inventory.py` | Admit/classify; `a_mode`/`b_mode` `"0"`/`"000000"` = absent side on add/delete |
| **GitLab runtime** | `gitlab_runtime.py` | Shared CapacityLimiter; per-call base_url/deadline; status map |
| **GitLab ops** | `gitlab_operations.py` | Pin exact MR diff version matching `diff_refs` |
| **Session** | `gitlab_diff_session.py` | open → pin via `run_blocking` → build inventory/content/assemble → aclose |
| **Register provider** | `domain/vcs_provider_registry.py` | `supports_repository(url)` auto-detect |

## CONVENTIONS
- Map provider models → domain entities at the boundary (`FileDiffResponse`, `PRDiff`).
- Use shared retry/security utilities where applicable.
- URL detection: GitHub.com PR paths vs any HTTPS host with `/-/merge_requests/` (custom GitLab).
- GitLab renames set `FileDiffResponse.previous_path` from `old_path` when distinct; no retrieval redesign.
- Prefer domain interfaces (`PRDiffRepositoryInterface` / `VCSDiffRepositoryInterface`) for registration.
- **GitLabRuntime**: process-shared limiter only; **per-call** `base_url` + `deadline_monotonic` (never shared mutable request state); each `run_blocking` uses a fresh client closed in `finally`; `abandon_on_cancel=False`; post-worker wall-clock deadline → E5004; inject `max_retries`/`obey_rate_limit` via `http_request` defaults (python-gitlab 8.5).
- **Host allowlist**: `GitLabConfig.allowed_hosts` (default `gitlab.com`); env `GITLAB_ALLOWED_HOSTS` CSV; `ensure_host_allowed` rejects non-allowlisted hosts before SDK (E1001).
- **Session open**: pin snapshot via `runtime.run_blocking(ops.select_with_client, base_url=…, deadline=…)` — never block the event loop on direct `select_diff_snapshot`.
- **Content fetch**: forward per-request `base_url` + `deadline_monotonic` into every raw content `run_blocking`.
- **Cache identity**: host from `cache_host_from_base_url` (port-aware for non-80/443).
- **Equal-noop**: equal-content equal-mode modified → hard E5020 `DIFF_GENERATION_FAILED`.
- Status map: 401→E2006, 403→E2007, 404→context (E4001/E4002/E4003), 429→E3006 (no local re-loop), 5xx→E5021, timeout→E5004, connection→E5019.

## ANTI-PATTERNS
- NO provider-specific types leaking to application tools.
- NO live API calls in unit tests.
- NO sharing SDK client objects across workers.
- NO second 429 retry loop outside SDK policy.
- NO `response_body` / tokens in mapped exception details.
- NO registering providers only in infrastructure without domain registry support.
- NO shared request deadline/base_url on process-wide `GitLabRuntime` instance state.
- NO calling python-gitlab on the event loop (always `run_blocking` / `to_thread`).
- NO open host + token SSRF: always enforce `allowed_hosts` before client create.
- NO partial full-diff success or silent equal-noop modified records.
