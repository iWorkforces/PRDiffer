# AGENTS.md - Domain Use Case Unit Tests

5 test modules, ~690 lines.

## STRUCTURE
```
tests/unit/domain/usecases/
├── test_pr_diff_usecases.py           # 235 — GetPRDiff + cache keying
├── test_pr_approval_usecases.py       # 159
├── test_pr_description_usecases.py    # 136
├── test_session_pr_diff_usecase.py    # 131 — session-capable vs legacy reader dispatch
└── test_pr_diff_usecases_purity.py    # 31 — AST import purity checks
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| **Session PRDiff** | `test_session_pr_diff_usecase.py` | Session build/aclose, fallback to legacy reader |
| **Diff cache keys** | `test_pr_diff_usecases.py` | GitHub vs GitLab cache key prefixes |
| **Domain isolation** | `test_pr_diff_usecases_purity.py` | No `prdiffer.application` imports |

## CONVENTIONS
- Mock service/repository interfaces only.
- `*_purity` tests guard domain isolation regressions (AST walk of use case modules).
- Async use cases: use asyncio.run or pytest-asyncio consistent with neighbors.

## ANTI-PATTERNS
- NO real provider clients.
- NO infrastructure factory wiring in use case unit tests.
