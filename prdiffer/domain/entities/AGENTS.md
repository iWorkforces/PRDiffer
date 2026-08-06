# AGENTS.md - Domain/Entities

Frozen (mostly) domain models for PR diffs, content results, cache entries, and repository metadata. Package 0.6.2.

## STRUCTURE
```
prdiffer/domain/entities/
├── file_patch.py            # FilePatchInfo + EDIT_TYPE — rich model (+ optional modes) (~347)
├── file_diff_response.py    # FileDiffResponse, FileStats (~54)
├── file_content.py          # Content union + multi-ref request/response (~58)
├── generated_file_diff.py   # GeneratedFileDiff (~19)
├── pr_diff_cache.py         # StrictPRDiffCacheIdentity + GitHub v2 / GitLab v1 keys (~134)
├── pr_diff.py               # PRDiff — files tuple of FileDiffResponse (~17)
├── pull_request.py          # PullRequest + PRState (~61)
├── repository.py            # Repository (~37)
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Business methods** | `file_patch.py` | `calculate_review_priority`, `detect_code_smells`, `validate` |
| **MCP file payload** | `file_diff_response.py` | path, status, stats, diff, `previous_path` (renames only) |
| **Typed content** | `file_content.py` | Available empty text vs deterministic unavailability |
| **Multi-ref identity** | `file_content.py` | `FileContentRequest` / `FileContentResponse` for cross-ref batches |
| **Generated unit** | `generated_file_diff.py` | index + path + previous_path + full-context `diff` |
| **Strict cache identity** | `pr_diff_cache.py` | `StrictPRDiffCacheIdentity`; GitHub v2 / GitLab v1 key builders |
| **Aggregate response** | `pr_diff.py` | `files: tuple[FileDiffResponse, ...]` |
| **PR / repo VO** | `pull_request.py`, `repository.py` | Pure metadata (non-frozen dataclasses) |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `EDIT_TYPE` | StrEnum | `file_patch.py` | added/deleted/modified/renamed/unknown |
| `FilePatchInfo` | Frozen dataclass | `file_patch.py` | Rich file change model; optional `old_mode`/`new_mode` (six-digit octal) |
| `FileStats` | Frozen dataclass | `file_diff_response.py` | additions/deletions |
| `FileDiffResponse` | Frozen dataclass | `file_diff_response.py` | Public MCP file payload |
| `FileContentAvailable` | Frozen dataclass | `file_content.py` | Successful text (incl. empty) |
| `FileContentUnavailable` | Frozen dataclass | `file_content.py` | Deterministic unavailability |
| `FileContentUnavailableReason` | StrEnum | `file_content.py` | BINARY, SIZE, DIRECTORY, NOT_FOUND, DECODE |
| `FileContentResult` | Alias | `file_content.py` | Available \| Unavailable |
| `FileContentRequest` | Frozen slotted dataclass | `file_content.py` | `(repo_full_name, path, ref)` lookup identity |
| `FileContentResponse` | Frozen slotted dataclass | `file_content.py` | Request + `FileContentResult` pair |
| `GeneratedFileDiff` | Frozen dataclass | `generated_file_diff.py` | One generated full-context file |
| `PRDiff` | Frozen dataclass | `pr_diff.py` | Aggregate files tuple |
| `StrictPRDiffCacheIdentity` | Frozen dataclass | `pr_diff_cache.py` | cache_key + validation_token + schema_version |
| `PRDiffCacheEntryV2` | Frozen dataclass | `pr_diff_cache.py` | schema_version=2 + PRDiff |
| `github_full_diff_v2_key` | Function | `pr_diff_cache.py` | Exact GitHub session/v2 cache key |
| `github_full_diff_v2_identity` | Function | `pr_diff_cache.py` | GitHub identity (key + head_sha token) |
| `gitlab_full_diff_v1_key` | Function | `pr_diff_cache.py` | `gitlab-full-diff-v1:{host}:{ns}:{repo}:{iid}:{ver}:{base}:{start}:{head}` |
| `gitlab_full_diff_v1_identity` | Function | `pr_diff_cache.py` | GitLab identity (host-aware key + version/refs token) |
| `PullRequest` / `PRState` | Entity | `pull_request.py` | PR metadata |
| `Repository` | Entity | `repository.py` | Repo metadata |

## CONVENTIONS
- Prefer `@dataclass(frozen=True)` for diff/content/cache models; multi-ref types also use `slots=True`.
- Rich logic stays on `FilePatchInfo`; response DTOs stay thin.
- Map infrastructure patches → `FileDiffResponse` at the adapter boundary.
- `FileDiffResponse.previous_path` is optional and valid **only** for `EDIT_TYPE.RENAMED` (`__post_init__` invariant; must differ from `path`). Success responses remain complete by construction — no completeness boolean.
- GitLab maps `old_path` → `previous_path` on renames only; otherwise `None`.
- Content: operational failures (auth, rate limit, transport) **raise**; do not fold into `FileContentUnavailable`.
- Same path at different refs yields **distinct** `FileContentRequest` values (identity includes `ref`).
- Cache helpers: `wrap_pr_diff_for_cache`, `unwrap_pr_diff_cache_value` (accept schema entry or bare `PRDiff` under strict GitHub-v2 / GitLab-v1 key prefixes).
- Sessions expose `StrictPRDiffCacheIdentity` (provider-neutral); GitHub keys remain byte-stable; GitLab keys include **host** (port-aware for non-80/443) for multi-instance correctness.

## ANTI-PATTERNS
- NO I/O or framework types.
- NO Pydantic `BaseModel` in this package.
- NO mutating frozen fields after construction.
- NO storing unversioned/v1 PRDiff under the full-diff-v2 path without key/schema discipline.
- NO treating binary/size/decode limits as soft partial success in the public response.
- NO conflating path-only identity with path+ref multi-ref batches.
