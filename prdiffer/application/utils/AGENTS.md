# AGENTS.md - Application/Utils

Application helpers for MCP tool parameter handling.

## STRUCTURE
```
prdiffer/application/utils/
├── pr_url_parser.py   # Parse/validate PR URLs (87) — parse_pr_url, parse_pr_target, PRTarget
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **GitHub PR URL** | `parse_pr_url()` | Returns `(owner, repo, number)` via `InputValidatorProtocol` |
| **Provider-aware target** | `parse_pr_target()` | Frozen `PRTarget` for GitHub or GitLab (incl. custom hosts) |
| **PRTarget model** | `PRTarget` dataclass | `provider`, `repo_owner`, `repo_name`, `pr_number`, optional `base_url` |

## CONVENTIONS
- Prefer injected `InputValidatorProtocol`; factory fallback for default validator is transitional.
- Raise domain validation errors (`InvalidURLError`, etc.), not raw `ValueError`, at the tool boundary.
- Used by `ToolRegistry` (`get_pr_diff` uses `parse_pr_target` for GitHub/GitLab routing).

## ANTI-PATTERNS
- NO provider SDK calls from utils.
- NO business rules (diff completeness, prioritization) in URL helpers.
