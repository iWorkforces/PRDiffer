# AGENTS.md - Infrastructure VCS Providers

Multi-provider VCS abstraction: GitHub, GitLab, extensible.

## OVERVIEW
VCS provider implementations with VCSDiffRepositoryInterface. Auto-detection via registry.

## STRUCTURE
```
prdiffer/infrastructure/vcs_providers/
├── github_repository.py    # GitHubVCSRepository
├── gitlab_repository.py    # GitLabVCSRepository (mock/stub)
└── *repository.py         # Additional providers
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add provider** | New *_repository.py | Implement VCSDiffRepositoryInterface |
| **Register provider** | `domain/vcs_provider_registry.py` | Use register_provider() |
| **GitHub impl** | `github_repository.py` | Wraps GitHubPRDiffRepository |
| **GitLab impl** | `gitlab_repository.py` | Stub implementation |

## CONVENTIONS

- Implement VCSDiffRepositoryInterface
- Async methods only
- URL pattern matching
- Register in VCSProviderRegistry

## ANTI-PATTERNS

- **NO synchronous code** → Async only
- **NO direct API calls** → Use infrastructure services
