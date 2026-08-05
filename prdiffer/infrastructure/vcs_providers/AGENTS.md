# AGENTS.md - VCS Providers

**Package:** 0.6.0  
GitHub and GitLab adapters implementing domain VCS/repository ports.

## STRUCTURE
```
prdiffer/infrastructure/vcs_providers/
├── github_repository.py    # GitHubVCSRepository + factory (147)
├── gitlab_repository.py    # GitLabVCSRepository (94)
├── gitlab_operations.py    # GitLab API operations / pagination (94)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **GitHub adapter** | `github_repository.py` | Wraps `infrastructure/github_repository.GitHubPRDiffRepository` |
| **Primary GitHub PR repo** | `../github_repository.py` | Main implementation (sibling module, not this package) |
| **GitLab adapter** | `gitlab_repository.py` | anyio `to_thread` for blocking python-gitlab |
| **GitLab ops** | `gitlab_operations.py` | Pagination, unidiff records, MR fetch |
| **Register provider** | `domain/vcs_provider_registry.py` | `supports_repository(url)` auto-detect |

## CONVENTIONS
- Map provider models → domain entities at the boundary (`FileDiffResponse`, `PRDiff`).
- Use shared retry/security utilities where applicable.
- URL detection must not false-positive across hosts (`github.com` vs `gitlab.com` patterns).
- GitLab renames set `FileDiffResponse.previous_path` from `old_path` when distinct; no retrieval redesign.
- Prefer domain interfaces (`PRDiffRepositoryInterface` / `VCSDiffRepositoryInterface`) for registration.

## ANTI-PATTERNS
- NO provider-specific types leaking to application tools.
- NO live API calls in unit tests.
- NO registering providers only in infrastructure without domain registry support.
