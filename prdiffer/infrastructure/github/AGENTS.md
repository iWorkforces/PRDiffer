# AGENTS.md - Infrastructure/GitHub

**Package:** 0.6.0  
PyGithub-backed API client, inventory admission, ordered file processing, full-context diff generation, and request sessions. Critical path for full-diff correctness.

## STRUCTURE
```
prdiffer/infrastructure/github/
├── client.py                # GitHubAPIClient facade (280)
├── client_operations.py     # File content / batch / cache mixin (431)
├── client_models.py         # Exception tuples + cache defaults (16)
├── file_processor.py        # Ordered fetch/filter → FilePatchInfo (544)
├── diff_generator.py        # generate_ordered_file_diffs → GeneratedFileDiff (468)
├── etag_adapter.py          # Conditional requests / 304 (121)
├── inventory.py             # Authoritative inventory + admission (126)
├── mappers.py               # API → domain mapping (88)
├── pr_diff_session.py       # anyio session isolation + cache_identity
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **API client facade** | `client.py` | Implements `GitHubAPIServiceInterface`; retry/CB params |
| **File content + batch** | `client_operations.py` | Typed content union; repo-scoped content cache |
| **Inventory admission** | `inventory.py` | Authoritative `changed_files` vs enumeration; selected N+1 → E5020 |
| **Ordered file processing** | `file_processor.py` | Deleted/rename-only included; head/base fetch |
| **Full-context diffs** | `diff_generator.py` | `GeneratedFileDiff` in provider order; hard-fail incompleteness |
| **Request session** | `pr_diff_session.py` | anyio `to_thread` + CapacityLimiter; one metadata lookup per request |
| **ETag bandwidth** | `etag_adapter.py` | Conditional GET / 304 |
| **Domain mapping** | `mappers.py` | Repository / PR → domain entities |

## CONVENTIONS

### Typed file content
- `get_file_content` / batch APIs return `FileContentAvailable | FileContentUnavailable`.
- Empty text is **available** (`text == ""`).
- Cache key is `(repo_full_name, path, immutable_ref)`; **only available text** is cached.
- Auth / rate-limit / transport / retry-exhausted failures raise operational exceptions — never become unavailable union values.

### Inventory (strict)
- Fully materialize provider file pages, then validate authoritative `changed_files` vs enumerated count.
- Authoritative count > 3000 → inventory truncated (E5020 path).
- Ignore/extension filter, then **selected-file admission**: exactly N succeeds; N+1 → `FILE_COUNT_LIMIT` (E5020).

### Ordered processing + generation
- `FileProcessor` assembles ordered `FilePatchInfo` (including deleted / rename-only).
- `DiffGenerator.generate_ordered_file_diffs` returns one full-context `GeneratedFileDiff` per selected file in order, or hard-fails.
- When `old_mode`/`new_mode` are both set and differ, prepend deterministic `old mode`/`new mode` headers (before rename headers).
- Contract inability → **E5020** / `FullDiffIncompleteError`; unexpected defects → E5003.

### Sessions
- `GitHubPRDiffSession` / `GitHubSessionPRDiffReader`: request-local client/repo/PR handles.
- Blocking PyGithub work via `anyio.to_thread.run_sync` with CapacityLimiter (capacity 1 when parallel fetch disabled).
- One metadata lookup per request; always close/drop strong refs in `aclose`.
- `cache_identity` returns byte-stable GitHub v2 key + `head_sha` validation token (`github_full_diff_v2_identity`).

### Boundary
- Never return raw PyGithub objects past this package boundary.
- Respect rate limits (403/429) via retry utilities.
- Honor ignore patterns / extension allowlists from settings/`GitHubConfig`.

## ANTI-PATTERNS
- NO domain imports of `github.*` SDK.
- NO unbounded file downloads without size limits.
- NO caching unavailable sentinels or empty-string error stand-ins.
- NO completing full-diff with partial file sets when inventory/admission fails.
- NO second metadata lookup inside an open session when handles already exist.
