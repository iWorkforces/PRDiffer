# AGENTS.md - Infrastructure/Services

**Package:** 0.6.0  
Concrete service adapters implementing domain service ports.

## STRUCTURE
```
prdiffer/infrastructure/services/
└── pr_diff_service.py   # GitHubPRDiffService (527) — CachingMixin + PRDiffServiceInterface
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **High-level PR diff** | `pr_diff_service.py` | Orchestrates GitHub API + inventory + processor + generator + cache |
| **Session path** | `open_pr_diff_session` | Delegates to `github/pr_diff_session.GitHubSessionPRDiffReader` |
| **Strict assembly** | `_build_pr_diff_strict` | `GeneratedFileDiff` → `FileDiffResponse`; size limits |
| **Inventory** | `_generate_diff_content*` | `prepare_selected_inventory` then ordered processing |

## CONVENTIONS
- Implements `PRDiffServiceInterface`; composes `github/` + `cache/` rather than duplicating logic.
- Maps ordered `GeneratedFileDiff` results to `FileDiffResponse` (`path`, `status`, `stats`, `diff`, `previous_path`).
- Enforces per-file and aggregate public-diff character limits via `utils/diff_limits` (hard fail, no truncation).
- Method-level caching via `CachingMixin` / `@cached_method`; use-case commit-based caching may layer above.
- Full-diff incompleteness raises `FullDiffIncompleteError` → **E5020**; unexpected generation defects → E5003.
- Prefer injecting `GitHubAPIClient`, `FileProcessor`, `DiffGenerator` (factory-wired from `GitHubConfig`).

## ANTI-PATTERNS
- NO MCP/tool concerns here (application layer).
- NO returning partial file lists when inventory/admission/generation fails.
- NO truncating public diffs on the full-diff path.
- NO second full metadata open when a session path already holds repo/PR handles.
