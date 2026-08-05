# AGENTS.md - Domain Entity Unit Tests

5 files, 1928 lines.

## STRUCTURE
```
tests/unit/domain/entities/
├── test_file_patch_info.py      # 652 — priority, smells, validate
├── test_pull_request.py         # 569
├── test_repository.py           # 252
├── test_pr_diff.py              # 238
└── test_file_diff_response.py   # 217
```

## CONVENTIONS
- Class groups: creation → properties → methods → immutability/serialization.
- Prefer frozen-instance tests for immutability guarantees.

## ANTI-PATTERNS
- NO framework dependencies in entity tests.
