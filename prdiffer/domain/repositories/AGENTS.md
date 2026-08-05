# AGENTS.md - Domain/Repositories

Repository ports for PR diff access. Package 0.6.0.

## STRUCTURE
```
prdiffer/domain/repositories/
├── pr_diff_repository.py   # PRDiffRepositoryInterface (~116)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **PR diff port** | `pr_diff_repository.py` | Implemented by GitHub/GitLab repositories |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `PRDiffRepositoryInterface` | ABC | `pr_diff_repository.py` | Repo-scoped PR operations |

### Methods / properties
- Properties: `repo_owner`, `repo_name`, `pr_number`
- `initialize()` — connect/validate before ops
- `get_pr_diff()` → `PRDiff`
- `get_latest_commit_sha()` → `str`
- `approve_pr_with_comment(pr_url, compliment)` → success message
- `update_pr_description(pr_url, description)` → success message

## CONVENTIONS
- Repositories return domain entities, not raw API models.
- Implementations: `infrastructure/github_repository.py`, `infrastructure/vcs_providers/`.
- Use cases for approve/describe inject this interface; diff fetch may also use service/reader ports.

## ANTI-PATTERNS
- NO PyGithub / httpx / python-gitlab types in signatures.
- NO I/O defaults or concrete clients in this package.
