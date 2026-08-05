# AGENTS.md - Domain/Repositories

Repository ports for PR diff access.

## STRUCTURE
```
prdiffer/domain/repositories/
├── pr_diff_repository.py   # PRDiffRepositoryInterface
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **PR diff port** | `pr_diff_repository.py` | Implemented by GitHub/GitLab repositories |

## CONVENTIONS
- Repositories return domain entities, not raw API models.
- Implementations: `infrastructure/github_repository.py`, `infrastructure/vcs_providers/`.

## ANTI-PATTERNS
- NO PyGithub / httpx types in signatures.
