# AGENTS.md - Domain Use Case Unit Tests

4 test modules, ~561 lines.

## STRUCTURE
```
tests/unit/domain/usecases/
├── test_pr_diff_usecases.py           # 235
├── test_pr_approval_usecases.py       # 159
├── test_pr_description_usecases.py    # 136
└── test_pr_diff_usecases_purity.py    # 31 — import purity checks
```

## CONVENTIONS
- Mock service/repository interfaces only.
- `*_purity` tests guard domain isolation regressions.

## ANTI-PATTERNS
- NO real provider clients.
