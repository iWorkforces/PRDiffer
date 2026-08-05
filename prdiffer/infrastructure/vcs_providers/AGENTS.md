# AGENTS.md - VCS Providers

GitHub and GitLab adapters implementing domain VCS/repository ports (~329 lines).

## STRUCTURE
```
prdiffer/infrastructure/vcs_providers/
├── github_repository.py    # GitHub VCS adapter / factory (147)
├── gitlab_repository.py    # GitLabVCSRepository (87)
├── gitlab_operations.py    # GitLab API operations (94)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add provider** | New `*_repository.py` | Implement `VCSDiffRepositoryInterface` |
| **Register** | `domain/vcs_provider_registry.py` | `supports_repository(url)` |
| **GitLab ops** | `gitlab_operations.py` | Pagination, diffs |
| **Primary GitHub PR repo** | `infrastructure/github_repository.py` | Main PRDiff repository (sibling package) |

## CONVENTIONS
- Map provider models → domain entities at the boundary.
- Use shared retry/security utilities.
- URL detection must not false-positive across hosts.

## ANTI-PATTERNS
- NO provider-specific types leaking to application tools.
