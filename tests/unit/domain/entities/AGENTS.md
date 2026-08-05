# AGENTS.md - Domain Entity Unit Tests

5 files, ~2.0K lines.

## STRUCTURE
```
tests/unit/domain/entities/
├── test_file_patch_info.py      # 652 — priority, smells, validate
├── test_pull_request.py         # 569
├── test_file_diff_response.py   # 275 — FileStats + previous_path rename rules
├── test_repository.py           # 252
└── test_pr_diff.py              # 238
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| **Priority / smells** | `test_file_patch_info.py` | Review priority, code smells, validate |
| **Rename previous_path** | `test_file_diff_response.py` | Only valid for RENAMED; rejects identical path |
| **PRDiff aggregate** | `test_pr_diff.py` | Frozen files tuple, replace/copy |
| **PR / repo value objects** | `test_pull_request.py`, `test_repository.py` | Refs, immutability |

## CONVENTIONS
- Class groups: creation → properties → methods → immutability/serialization.
- Prefer frozen-instance tests for immutability guarantees.
- Cover `FileDiffResponse.previous_path` for rename-only semantics.

## ANTI-PATTERNS
- NO framework dependencies in entity tests.
- NO infrastructure or MCP imports.
