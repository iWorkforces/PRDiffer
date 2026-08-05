# AGENTS.md - Application/Utils

Application helpers for MCP tool parameter handling.

## STRUCTURE
```
prdiffer/application/utils/
├── pr_url_parser.py   # Parse/validate PR URLs (owner, repo, number)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **PR URL parsing** | `pr_url_parser.py` | GitHub-style URLs; validation errors → domain exceptions |

## CONVENTIONS
- Keep pure parsing where possible; use input validation ports for security checks.
- Raise domain validation errors, not raw ValueError, at the tool boundary.

## ANTI-PATTERNS
- NO provider SDK calls from utils.
