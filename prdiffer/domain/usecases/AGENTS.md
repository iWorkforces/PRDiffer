# AGENTS.md - Domain/Use Cases

Thin business orchestration over injected ports (~196 lines).

## STRUCTURE
```
prdiffer/domain/usecases/
├── pr_diff_usecases.py          # GetPRDiffUseCase (71)
├── pr_description_usecases.py   # Describe PR (62)
├── pr_approval_usecases.py      # Approve PR (62)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Fetch structured diff** | `pr_diff_usecases.py` | Coordinates repository/service ports |
| **Update description** | `pr_description_usecases.py` | |
| **Approve PR** | `pr_approval_usecases.py` | |

## CONVENTIONS
- Constructor-inject interfaces only.
- No framework, auth, or HTTP concerns (those live in application tools).
- Keep use cases short; push provider details to infrastructure.

## ANTI-PATTERNS
- NO direct VCS SDK usage.
- NO caching/retry implementation details.
