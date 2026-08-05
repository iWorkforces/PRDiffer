# AGENTS.md - Domain/Entities

Frozen domain models for PR diffs and repository metadata.

## STRUCTURE
```
prdiffer/domain/entities/          # + typed content results
├── file_patch.py                  # FilePatchInfo + EDIT_TYPE — rich model
├── file_diff_response.py          # FileDiffResponse, FileStats
├── file_content.py                # FileContentAvailable | FileContentUnavailable
├── generated_file_diff.py         # GeneratedFileDiff (index, path, previous_path, diff)
├── pr_diff_cache.py               # PRDiffCacheEntryV2 + github-full-diff-v2 keys
├── pr_diff.py                     # PRDiff — files tuple of FileDiffResponse
├── pull_request.py                # PullRequest
├── repository.py                  # Repository
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Business methods** | `file_patch.py` | `calculate_review_priority`, `detect_code_smells`, `validate` |
| **MCP file payload** | `file_diff_response.py` | path, status, stats, diff, `previous_path` (renames only) |
| **Typed content** | `file_content.py` | Available empty text vs deterministic unavailability |
| **Aggregate response** | `pr_diff.py` | `files: tuple[FileDiffResponse, ...]` |

## CONVENTIONS
- `@dataclass(frozen=True)` everywhere.
- Rich logic stays on `FilePatchInfo`; response DTOs stay thin.
- Map infrastructure patches → `FileDiffResponse` at the adapter boundary.
- `FileDiffResponse.previous_path` is optional and valid **only** for `EDIT_TYPE.RENAMED` (domain invariant in `__post_init__`). Success responses remain complete by construction — no completeness boolean.
- GitLab maps `old_path` → `previous_path` on renames only; otherwise `None`.

## ANTI-PATTERNS
- NO I/O or framework types.
- NO Pydantic `BaseModel` in this package.
- NO mutating fields after construction.
