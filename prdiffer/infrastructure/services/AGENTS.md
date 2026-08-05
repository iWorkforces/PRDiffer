# AGENTS.md - Infrastructure/Services

Concrete service adapters implementing domain service ports.

## STRUCTURE
```
prdiffer/infrastructure/services/
└── pr_diff_service.py   # GitHubPRDiffService (408) — CachingMixin + PRDiffServiceInterface
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **High-level PR diff** | `pr_diff_service.py` | Orchestrates GitHub repo/API + cache |

## CONVENTIONS
- Implement domain interfaces.
- Compose lower-level github/ and cache/ modules rather than duplicating logic.

## ANTI-PATTERNS
- NO MCP/tool concerns here (those are application layer).
