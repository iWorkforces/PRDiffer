# AGENTS.md - Domain/Entities

Frozen domain models for PR diffs and repository metadata.

## STRUCTURE
```
prdiffer/domain/entities/          # 488 lines total
├── file_patch.py                  # FilePatchInfo + EDIT_TYPE (329) — rich model
├── file_diff_response.py          # FileDiffResponse, FileStats (43)
├── pr_diff.py                     # PRDiff (17) — files tuple of FileDiffResponse
├── pull_request.py                # PullRequest (61)
├── repository.py                  # Repository (37)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Business methods** | `file_patch.py` | `calculate_review_priority`, `detect_code_smells`, `validate` |
| **MCP file payload** | `file_diff_response.py` | path, status, stats, diff |
| **Aggregate response** | `pr_diff.py` | `files: tuple[FileDiffResponse, ...]` |

## CONVENTIONS
- `@dataclass(frozen=True)` everywhere.
- Rich logic stays on `FilePatchInfo`; response DTOs stay thin.
- Map infrastructure patches → `FileDiffResponse` at the adapter boundary.

## ANTI-PATTERNS
- NO I/O or framework types.
- NO Pydantic `BaseModel` in this package.
- NO mutating fields after construction.
