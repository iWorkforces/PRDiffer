# AGENTS.md - Infrastructure/GitHub

**Package:** 0.6.2  
PyGithub-backed API client, inventory admission, ordered file processing, full-context diff generation, and request sessions. Critical path for full-diff correctness.

## STRUCTURE
```
prdiffer/infrastructure/github/
├── client.py                # GitHubAPIClient facade (~280)
├── client_operations.py     # File content / multi-ref batch / cache mixin (~441)
├── client_models.py         # Exception tuples + cache defaults (~16)
├── file_processor.py        # Ordered fetch/filter → FilePatchInfo (~593)
├── diff_generator.py        # generate_ordered_file_diffs → GeneratedFileDiff (~514)
├── etag_adapter.py          # Conditional requests / 304 (~121)
├── inventory.py             # Authoritative inventory + admission (~130)
├── mappers.py               # API → domain mapping (~88)
├── pr_diff_session.py       # anyio session + merge-base capture + v3 cache_identity + revalidate
└── __init__.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **API client facade** | `client.py` | Implements `GitHubAPIServiceInterface`; retry/CB params |
| **File content + batch** | `client_operations.py` | Typed content union; multi-ref batch; repo-scoped cache |
| **Multi-ref batch** | `get_files_content_multi_ref_batch` | Ordered `FileContentResponse`; one capacity bound for all refs |
| **Inventory admission** | `inventory.py` | Authoritative `changed_files` vs enumeration; selected N+1 → E5020 |
| **Ordered file processing** | `file_processor.py` | Deleted/rename-only included; multi-ref head/base when enabled |
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

### Multi-ref content batch
- `get_files_content_multi_ref_batch(requests)` returns one `FileContentResponse` per request in **request order**.
- Single-ref `get_files_content_batch` is implemented as a thin wrapper over multi-ref.
- Parallel path uses `execute_indexed_batch` on cache misses only; mixed hit/miss preserves order and ref identity.
- Operational failure → `IndexedBatchError` / raise — never a partial response list.
- Deduplicates identical `FileContentRequest` values while still emitting one response per input slot.

### Inventory (strict)
- Fully materialize provider file pages, then validate authoritative `changed_files` vs enumerated count.
- Authoritative count > 3000 → inventory truncated (E5020 path).
- Ignore/extension filter, then **selected-file admission**: exactly N succeeds; N+1 → `FILE_COUNT_LIMIT` (E5020).

### Ordered processing + generation
- `FileProcessor` assembles ordered `FilePatchInfo` (including deleted / rename-only).
- When `parallel_head_base_fetch_enabled` and both head and base path sets are non-empty: one interleaved multi-ref batch (head/base alternating in provider order), then split into head/base maps.
- Disabled flag or one-sided path sets: sequential single-ref batches.
- `DiffGenerator.generate_ordered_file_diffs` returns one full-context `GeneratedFileDiff` per selected file in order, or hard-fails.
- Mode headers (before rename, then body): `new file mode` / `deleted file mode` / `old mode`+`new mode` for 100644/100755/120000/160000.
- `DiffUtils` emits Git-style `\ No newline at end of file` when either side lacks a trailing newline.
- Never fall back to provider hunk text when reconstruction fails (E5003 / E5020 only).
- Contract inability → **E5020** / `FullDiffIncompleteError`; unexpected defects → E5003.

### Sessions
- `GitHubPRDiffSession` / `GitHubSessionPRDiffReader`: request-local client/repo/PR handles.
- Blocking PyGithub work via `anyio.to_thread.run_sync` with CapacityLimiter (capacity 1 when parallel fetch disabled).
- One metadata lookup per request; always close/drop strong refs in `aclose`.
- Open captures base tip + head + authoritative count, resolves **merge-base once** via Compare (no base-tip fallback), then returns the session.
- `cache_identity` returns GitHub v3 key + `merge_base:head` token (`github_full_diff_v3_identity`); base-tip-only churn does not change identity.
- `build_pr_diff` passes the immutable snapshot into generation and **revalidates** head/merge-base/count afterward; drift → E5020 `SNAPSHOT_CHANGED` (no cache write).

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
- NO path-only batch identity when head and base share paths at different refs.
