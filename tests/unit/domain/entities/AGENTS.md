# AGENTS.md - Domain Entity Unit Tests

7 files, ~2.2K lines.

## STRUCTURE
```
tests/unit/domain/entities/
├── test_file_patch_info.py           # 677 — priority, smells, validate
├── test_pull_request.py              # 569
├── test_file_diff_response.py        # 278 — FileStats + previous_path rename rules
├── test_repository.py                # 252
├── test_pr_diff.py                   # 238
├── test_pr_diff_cache.py             # StrictPRDiffCacheIdentity + GitHub v3 / legacy v2 rejection
└── test_file_content_multi_ref.py    # 16 — FileContentRequest/Response identity
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| **Priority / smells** | `test_file_patch_info.py` | Review priority, code smells, validate |
| **Rename previous_path** | `test_file_diff_response.py` | Only valid for RENAMED; rejects identical path |
| **PRDiff aggregate** | `test_pr_diff.py` | Frozen files tuple, replace/copy |
| **Strict cache identity** | `test_pr_diff_cache.py` | Frozen identity, GitHub v3 keys, v2 rejection |
| **Multi-ref content** | `test_file_content_multi_ref.py` | Same path different refs are distinct requests |
| **PR / repo value objects** | `test_pull_request.py`, `test_repository.py` | Refs, immutability |

## CONVENTIONS
- Class groups: creation → properties → methods → immutability/serialization.
- Prefer frozen-instance tests for immutability guarantees.
- Cover `FileDiffResponse.previous_path` for rename-only semantics.
- Multi-ref entities: assert path+ref identity, not path-only equality.

## ANTI-PATTERNS
- NO framework dependencies in entity tests.
- NO infrastructure or MCP imports.
