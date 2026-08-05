# gitlab-strict-full-diff - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** GitLab merge-request diffs that are rebuilt from one immutable version and the complete old/new file contents, in provider order. A successful response is complete; an incomplete, binary, oversized, unavailable, or indeterminate file fails the entire request with a structured error instead of returning a misleading empty or partial diff.

**Why this approach:** GitLab's ordinary diff text is limited hunk data and can be suppressed, while head SHA alone does not identify a stable target comparison. Pinning the exact diff version and all three commit references makes inventory, content, cache identity, and output internally consistent.

**What it will NOT do:** It will not add self-managed GitLab support, use deprecated or deployment-sensitive diff endpoints, return partial/binary placeholders, reuse legacy hunk-only cache values, or change GitHub behavior.

**Effort:** XL
**Risk:** High - correctness spans provider snapshots, content acquisition, caching, async cancellation, public MCP errors, and shared diff generation.
**Decisions to sanity-check:** GitLab.com only; exact version/ref match with no fallback; binary and unsupported states fail closed; legacy GitLab cache entries are ignored; nested namespaces ship in the same delivery.

Your next move: start the plan in a worker session or request the optional dual high-accuracy plan review. Full execution detail follows below.

---

> TL;DR (machine): XL/high-risk GitLab-only strict full-diff pipeline with immutable version identity, pinned content, fail-closed E5020, bounded SDK execution, structured MCP errors, nested namespaces, and complete regression evidence.

## Scope
### Must have
- A request-scoped GitLab session pinned to one MR diff version whose `base_commit_sha`, `start_commit_sha`, and `head_commit_sha` exactly match the MR's current `diff_refs`.
- A provider-neutral session cache identity contract. GitHub must keep its existing `github-full-diff-v2` key and output byte-for-byte; GitLab must use `gitlab-full-diff-v1` with version ID plus all three immutable refs and must ignore every legacy `gitlab:<owner>:<repo>:<iid>` hunk-only entry.
- An authoritative, ordered inventory taken only from the selected version's embedded `diffs`, with collected-state validation, exact `real_size` cardinality, file-count admission, modes, generated-file metadata, and fail-closed handling of missing/unknown/limited records.
- Ref-pinned raw content retrieval for added, deleted, modified, renamed, rename-only, zero-byte, generated, and mode-only files. Required content that is missing, binary, oversized, or undecodable aborts the entire result with `E5020_FULL_DIFF_INCOMPLETE`.
- Full-context generation for every admitted file in provider order, including rename and mode headers, correct additions/deletions, per-file and aggregate limits, and no hunk-only or partial success path.
- GitLab-specific configuration, bounded AnyIO worker capacity, operation-aligned client timeouts, SDK transient 5xx retries, SDK rate-limit obedience, status-aware exception mapping, and operation-scoped client cleanup.
- A machine-readable MCP E5020 error body preserved at the raw FastMCP `call_tool` boundary with `isError=true` and no partial `files` data.
- Canonical GitLab.com nested namespaces such as `group/subgroup/project`; full anchoring and rejection of self-managed hosts, malformed paths, query/fragment suffixes, and encoded separator tricks.
- TDD unit, integration, raw MCP, deterministic concurrency/deadline, cross-provider regression, lint, format, type, architecture-baseline, and full-suite evidence.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- No self-managed GitLab base URL/configuration, OAuth/job-token expansion, GraphQL path, webhook work, or GitLab approval/description tools.
- No `/changes`, unversioned current `/diffs`, `/raw_diffs`, `access_raw_diffs`, `changes_count` completeness proof, manual page-number fallback, or alphabetic reordering in the strict path.
- No partial `files` array, truncation marker, binary placeholder, successful empty diff for a suppressed/unknown state, legacy hunk compatibility mode, or cache of partial/unavailable/E5020 results.
- No independent 429 retry loop and no retries for 401, 403, 404, or 422. Preserve python-gitlab's `obey_rate_limit=True` behavior.
- No live GitLab calls in tests and no dependency upgrade unless the locked python-gitlab version demonstrably lacks a required documented API.
- No GitHub response, ordering, cache-key, filtering, timeout, or error behavior changes. Shared contract edits require explicit GitHub regression assertions in the same todo.
- No attempt to repair the pre-existing `application.factory -> infrastructure.factories.infrastructure_factory` analyzer violation; the gate is zero new violations.
- No source module above 250 pure LOC without a narrowly documented `SIZE_OK` exception; extract `gitlab_models.py`, `gitlab_runtime.py`, `gitlab_content.py`, and `gitlab_diff_session.py` rather than growing one adapter into a monolith.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: strict red -> green -> refactor TDD with pytest/pytest-asyncio; every todo first records a failing focused test, then the minimum implementation, then focused regression evidence.
- Test shape: pure model/key/status tests; HTTP-SDK seam tests with narrow fake managers/exceptions; AnyIO concurrency/deadline tests; provider integration with an in-memory cache and fake GitLab SDK; raw FastMCP `call_tool` success/error assertions; no live network.
- Evidence root: `<attemptDir>` is `currentAttemptDir` from `omo ulw-loop status --json`; outside ulw-loop use `.omo/evidence/`. Store full command output as `<attemptDir>/task-{task-number}-gitlab-strict-full-diff.txt`; final reviewers use `<attemptDir>/final-F{verifier-number}-gitlab-strict-full-diff.txt`.
- Per-todo static gate: run `lsp_diagnostics` on every changed Python file and `uv run ruff check <changed paths>`; tasks touching domain/infrastructure/application boundaries also run `uv run python scripts/analyze_dependencies.py --path prdiffer` and compare to the recorded one-violation baseline.
- Focused cumulative gate after each wave: `uv run pytest tests/unit/domain/test_gitlab_pr_diff_cache.py tests/unit/domain/usecases/test_session_pr_diff_usecase.py tests/unit/infrastructure/test_gitlab_operations.py tests/unit/infrastructure/test_gitlab_diff_pagination.py tests/unit/infrastructure/test_gitlab_file_content.py tests/unit/infrastructure/test_gitlab_vcs_provider.py tests/unit/infrastructure/vcs_providers/test_gitlab_diff_generator.py tests/unit/infrastructure/test_input_validator.py tests/unit/application/utils/test_pr_url_parser.py tests/unit/application/test_tool_registry.py tests/integration/test_gitlab_strict_full_diff.py tests/integration/test_full_diff_mcp_surface.py -v --tb=short`, omitting only files not yet created in earlier waves.
- Final repository gates: `uv lock --check`; `uv run ruff check .`; `uv run ruff format --check .`; `uv run ty check`; `uv run pytest tests -v --tb=short`; and `uv run python scripts/analyze_dependencies.py --path prdiffer` with exactly the pre-existing application-factory violation and no new GitLab-related edge.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.
- Wave 1 - contracts and invariants: todos 1-4 in parallel where files do not overlap; todo 1 is the shared cache/session seam, todo 2 config, todo 3 errors, todo 4 mode-aware generation.
- Wave 2 - independent boundaries: todos 5-7 after their Wave 1 prerequisites; runtime resilience, nested URL parsing, and MCP E5020 transport may proceed in parallel.
- Wave 3 - immutable acquisition: todo 8 pins the MR version first; todos 9 and 10 then run in parallel against that model; todo 11 assembles only after both succeed.
- Wave 4 - session and composition: todo 12 creates the GitLab strict session, todo 13 generalizes the use-case cache path, then todo 14 wires infrastructure/server composition.
- Wave 5 - end-to-end proof: todos 15-17 run in parallel after composition; todo 18 updates public/operator documentation only after behavior and QA evidence are stable.
- Final verification wave: F1-F4 run in parallel after todo 18; all four must approve the same worktree state.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | none | 12, 13 | 2, 3, 4 |
| 2 | none | 5, 10, 12, 14, 17 | 1, 3, 4 |
| 3 | none | 5, 7, 8, 9, 10, 11, 12, 16 | 1, 2, 4 |
| 4 | none | 11 | 1, 2, 3 |
| 5 | 2, 3 | 8, 9, 10, 12, 14, 17 | 6, 7 |
| 6 | none | 14, 15, 16 | 5, 7 |
| 7 | 3 | 16 | 5, 6 |
| 8 | 3, 5 | 9, 10, 11, 12 | none until snapshot model is fixed |
| 9 | 3, 5, 8 | 11, 12, 15 | 10 |
| 10 | 2, 3, 5, 8 | 11, 12, 15 | 9 |
| 11 | 3, 4, 8, 9, 10 | 12, 15 | none |
| 12 | 1, 2, 3, 5, 8, 9, 10, 11 | 13, 14, 15, 17 | none |
| 13 | 1, 12 | 14, 15, 16 | none |
| 14 | 2, 5, 6, 12, 13 | 15, 16, 17 | none |
| 15 | 6, 9, 10, 11, 12, 13, 14 | 18, F1-F4 | 16, 17 |
| 16 | 3, 6, 7, 13, 14 | 18, F1-F4 | 15, 17 |
| 17 | 2, 5, 12, 14 | 18, F1-F4 | 15, 16 |
| 18 | 15, 16, 17 | F1-F4 | none |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [x] 1. Generalize strict session cache identity while preserving GitHub v2 behavior
  - Recommended task executor category: `deep` - shared domain protocol and use-case changes have broad cache/caller blast radius and require exact compatibility proof.
  - What to do: In `prdiffer/domain/entities/pr_diff_cache.py`, add frozen `StrictPRDiffCacheIdentity(cache_key: str, validation_token: str, schema_version: int)` and GitLab v1 key/validation builders. Extend `prdiffer/domain/interfaces/pr_diff_reader.py` so every strict session exposes `cache_identity`; adapt `prdiffer/infrastructure/github/pr_diff_session.py` to return the existing `github-full-diff-v2:{owner}:{repo}:{pr}:{head_sha}` key byte-for-byte and `head_sha` validation token. Keep cache value schema v2 behavior unchanged. Add exact key/schema/immutability tests in `tests/unit/domain/test_gitlab_pr_diff_cache.py`, `tests/unit/domain/entities/test_pr_diff_cache.py`, and GitHub session regressions.
  - Must NOT do: Do not change GitHub key bytes, accept raw/legacy values under unversioned keys, add provider branching to the use case in this todo, or prepend `gitlab:` to the future strict cache key.
  - Parallelization: Wave 1 | Blocked by: none | Blocks: 12, 13.
  - References: `prdiffer/domain/entities/pr_diff_cache.py:1-46`; `prdiffer/domain/interfaces/pr_diff_reader.py:1-43`; `prdiffer/infrastructure/github/pr_diff_session.py:1-213`; `prdiffer/domain/usecases/pr_diff_usecases.py:61-100`; `tests/unit/domain/usecases/test_session_pr_diff_usecase.py`.
  - Acceptance criteria: `gitlab-full-diff-v1:{namespace.casefold()}:{repo.casefold()}:{iid}:{version_id}:{base_sha}:{start_sha}:{head_sha}` is exact; validation token contains version ID and all three refs; dataclass mutation raises; GitHub keys, cache hits, misses, and close-on-hit behavior remain exactly green.
  - QA scenarios: Happy - `uv run pytest tests/unit/domain/test_gitlab_pr_diff_cache.py tests/unit/domain/usecases/test_session_pr_diff_usecase.py tests/unit/infrastructure/github/test_pr_diff_session.py -v --tb=short` proves both providers' identities; Failure - inject a legacy GitLab key and wrong schema/token and assert cache unwrap returns `None` while the session remains closable. Evidence: `<attemptDir>/task-1-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `refactor(cache): make strict session cache identity provider-neutral`.

- [x] 2. Add validated GitLab strict-diff configuration and settings caching
  - Recommended task executor category: `quick` - a contained frozen configuration value object plus existing SettingsService pattern.
  - What to do: Add `prdiffer/domain/config/gitlab_config.py` with a frozen, slotted `GitLabConfig`; add typed `get_gitlab_config()` to `prdiffer/domain/services/settings.py` and cached RLock-backed construction in `prdiffer/infrastructure/settings.py`; add `gitlab.*` keys under the existing `[default]` table in `settings.toml`. Fields/defaults: `timeout=30`, `max_retries=3`, `max_concurrent=4`, `retry_transient_errors=true`, `obey_rate_limit=true`, `max_file_size_bytes=10_485_760`, `max_files_allowed=app.max_files_allowed`, `max_total_chars=diff.max_total_chars`, and `pr_diff_request_timeout_seconds=mcp.pr_diff_request_timeout_seconds`.
  - Must NOT do: Do not reuse `GitHubConfig`, add GitLab file-extension filtering, add an `lru_cache`, or create self-managed base-URL configuration.
  - Parallelization: Wave 1 | Blocked by: none | Blocks: 5, 10, 12, 14, 17.
  - References: `settings.toml:5-44`; `prdiffer/domain/config/github_config.py`; `prdiffer/domain/services/settings.py:5-59`; `prdiffer/infrastructure/settings.py:118-171`; `tests/unit/infrastructure/test_settings_manual_cache.py`; `tests/unit/infrastructure/test_github_config_wiring.py`.
  - Acceptance criteria: Construction rejects `timeout <= 0`, `timeout >= pr_diff_request_timeout_seconds`, negative retries, nonpositive concurrency/limits, and nonpositive total chars; environment/default lookup and manual cache clearing match the GitHub settings pattern; defaults resolve exactly to the values above.
  - QA scenarios: Happy - `uv run pytest tests/unit/domain/config/test_gitlab_config.py tests/unit/infrastructure/test_gitlab_config_wiring.py tests/unit/infrastructure/test_settings_manual_cache.py -v --tb=short`; Failure - parameterized invalid boundary values raise `ValueError` before any SDK client can be built. Evidence: `<attemptDir>/task-2-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `feat(config): add GitLab strict diff limits and resilience settings`.

- [x] 3. Define GitLab-specific operational error taxonomy and safe mappings
  - Recommended task executor category: `quick` - additive domain constants and focused exception types with strict uniqueness tests.
  - What to do: Add `E2006_GITLAB_AUTH_FAILED`, `E2007_GITLAB_INSUFFICIENT_PERMISSIONS`, `E3006_GITLAB_RATE_LIMITED`, and `E5021_GITLAB_API_ERROR` in `prdiffer/domain/error_codes.py` and re-export through `prdiffer/domain/errors.py`. Add `GitLabAPIError(PRDifferException)` with optional `status_code` in `prdiffer/domain/exceptions.py`. Reuse existing `AuthenticationError`, `AuthorizationError`, `RateLimitError`, `TimeoutError`, `E4001_REPO_NOT_FOUND`, `E4002_PR_NOT_FOUND`, `E5004_TIMEOUT_ERROR`, `E5019_CONNECTION_ERROR`, and `FullDiffIncompleteError` rather than inventing parallel categories.
  - Must NOT do: Do not alter GitHub error messages/codes, include `response_body`, tokens, URLs with credentials, or raw file content in details, and do not map operational auth/rate/network failures to E5020.
  - Parallelization: Wave 1 | Blocked by: none | Blocks: 5, 7, 8, 9, 10, 11, 12, 16.
  - References: `prdiffer/domain/error_codes.py:100-209`; `prdiffer/domain/exceptions.py:13-199,255-357,446-467`; `prdiffer/domain/errors.py:38-117`; `tests/unit/domain/test_error_codes.py`; `tests/unit/domain/test_exceptions.py`; `tests/unit/domain/test_full_diff_incomplete_error.py`.
  - Acceptance criteria: All error codes are globally unique; 401/403/429/5xx each have a provider-appropriate code/message/remediation; `GitLabAPIError` preserves safe status and structured details; E5020's nine-reason taxonomy remains unchanged.
  - QA scenarios: Happy - `uv run pytest tests/unit/domain/test_error_codes.py tests/unit/domain/test_errors.py tests/unit/domain/test_exceptions.py tests/unit/domain/test_full_diff_incomplete_error.py -v --tb=short`; Failure - constructing/logging a representative GitLab error with secret-like upstream fields proves they are never copied into public details. Evidence: `<attemptDir>/task-3-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `feat(errors): add GitLab API error codes`.

- [x] 4. Extend the shared full-context generator for explicit file-mode changes
  - Recommended task executor category: `unspecified-high` - shared entity and generator changes require ordered-diff and GitHub regression coverage.
  - What to do: Add optional `old_mode`/`new_mode` to `FilePatchInfo` in `prdiffer/domain/entities/file_patch.py`, validating Git-style six-digit octal mode strings only when present. Update `prdiffer/infrastructure/github/diff_generator.py` to prepend deterministic `old mode <mode>\nnew mode <mode>\n` when valid modes differ; compose mode headers with rename headers in stable order; mode-only files return status `modified`, additions/deletions `0/0`, and nonempty mode text. Keep absent modes behavior unchanged.
  - Must NOT do: Do not infer modes from nullable provider patches, emit a mode header when modes are equal/absent, change existing textual full-context bodies, or weaken unknown-status/binary/truncation failures.
  - Parallelization: Wave 1 | Blocked by: none | Blocks: 11.
  - References: `prdiffer/domain/entities/file_patch.py:17-329`; `prdiffer/infrastructure/github/diff_generator.py:60-231`; `prdiffer/domain/entities/generated_file_diff.py`; `tests/unit/domain/entities/test_file_patch_info.py`; `tests/unit/infrastructure/github/test_generated_file_diffs.py`; `tests/unit/infrastructure/github/test_diff_generator.py`.
  - Acceptance criteria: Valid `100644 -> 100755` produces exact mode headers; rename+mode ordering is deterministic; the shared model rejects malformed mode strings at construction; all GitHub fixtures with modes `None` produce byte-identical diffs and stats. Provider-level translation of malformed required modes to E5020 belongs to todo 9/11.
  - QA scenarios: Happy - `uv run pytest tests/unit/domain/entities/test_file_patch_info.py tests/unit/infrastructure/github/test_diff_generator.py tests/unit/infrastructure/github/test_generated_file_diffs.py -v --tb=short`; Failure - invalid modes are rejected and a directly constructed unknown edit type still raises `FullDiffIncompleteError` without a successful empty diff. Evidence: `<attemptDir>/task-4-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `feat(diff): generate deterministic file mode headers`.

- [x] 5. Build the bounded GitLab SDK execution runtime and status-aware exception mapper
  - Recommended task executor category: `deep` - cancellation, worker-thread lifetime, SDK retry semantics, limiter sharing, and typed error translation form one concurrency boundary.
  - What to do: Add `prdiffer/infrastructure/vcs_providers/gitlab_runtime.py` owning a process-shared `anyio.CapacityLimiter`, operation-scoped python-gitlab client factory, monotonic remaining-budget calculation, and one async blocking-call runner. Construct `gitlab.Gitlab("https://gitlab.com", private_token=..., timeout=min(config.timeout, remaining), retry_transient_errors=config.retry_transient_errors, max_retries=config.max_retries, obey_rate_limit=config.obey_rate_limit, max_retry_after=floor(remaining))`. Run each complete synchronous SDK callback with a fresh client, the shared limiter, and `anyio.fail_after(remaining)`; use abandon-on-cancel only because the callback owns and closes its client in the worker's `finally`, and track eventual worker cleanup in tests. Translate python-gitlab `response_code`: 401 auth, 403 permission, 404 only through an operation-supplied project/MR/file context, 429 rate limit with parsed bounded Retry-After, 5xx after SDK exhaustion to E5021, request timeout to E5004, and connection failure to E5019.
  - Must NOT do: Do not share SDK client objects across workers, add a second 429 loop, retry 401/403/404/422, treat timeout as cancellation success, expose `response_body`, or use the default global AnyIO limiter implicitly.
  - Parallelization: Wave 2 | Blocked by: 2, 3 | Blocks: 8, 9, 10, 12, 14, 17.
  - References: `prdiffer/infrastructure/vcs_providers/gitlab_operations.py:13-94`; `prdiffer/infrastructure/vcs_providers/gitlab_repository.py:33-56`; `prdiffer/application/pr_diff_executor.py:21-76`; `prdiffer/domain/config/gitlab_config.py` from todo 2; python-gitlab client options documented at `https://python-gitlab.readthedocs.io/en/stable/api/gitlab.html`; AnyIO thread semantics at `https://anyio.readthedocs.io/en/stable/threads.html`.
  - Acceptance criteria: Fake SDK tests prove exact constructor arguments, maximum observed active workers never exceeds config, transient 5xx attempts equal configured bounds, 429 uses SDK policy without local reattempt, operation timeout returns E5004 before owner deadline, and every client closes on success/error/cancellation.
  - QA scenarios: Happy - `uv run pytest tests/unit/infrastructure/vcs_providers/test_gitlab_runtime.py -v --tb=short` with four concurrent operations and configured capacity two; Failure - inject 401/403/404/429/500/timeout/connection cases and assert exact type/code/retry count plus cleanup. Evidence: `<attemptDir>/task-5-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `feat(gitlab): bound SDK operations and map statuses`.

- [x] 6. Support canonical nested GitLab.com namespaces end to end
  - Recommended task executor category: `quick` - deterministic parser/matcher hardening with existing validation seams.
  - What to do: Update `prdiffer/application/utils/pr_url_parser.py`, `prdiffer/infrastructure/utils/url_parser.py`, `prdiffer/infrastructure/security/input_validator.py`, and `GitLabVCSRepository.supports_repository()` to parse the complete project path immediately before `/-/merge_requests/<iid>`, split only at its final slash, carry `group/subgroup` in `PRTarget.repo_owner`, and pass `group/subgroup/project` unencoded to python-gitlab `projects.get`. Fully anchor GitLab.com canonical URLs with optional trailing slash only.
  - Must NOT do: Do not route nested GitLab owners through GitHub `_validate_owner`; do not accept self-managed hosts, `/tree`, missing project segments, duplicate separators, dot/traversal segments, percent-encoded `/` or `\\`, nonnumeric/zero/overflow IID, query strings, or fragments.
  - Parallelization: Wave 2 | Blocked by: none | Blocks: 14, 15, 16.
  - References: `prdiffer/application/utils/pr_url_parser.py:15-22,65-87`; `prdiffer/infrastructure/utils/url_parser.py:75-107`; `prdiffer/infrastructure/security/input_validator.py`; `prdiffer/infrastructure/vcs_providers/gitlab_repository.py:91-94`; `tests/unit/application/utils/test_pr_url_parser.py:189-218`; `tests/unit/infrastructure/test_input_validator.py:103-114`.
  - Acceptance criteria: `https://gitlab.com/group/subgroup/project/-/merge_requests/42` yields provider `gitlab`, owner `group/subgroup`, repo `project`, IID 42, and provider support true; every malformed case above is rejected by parser, input validator, and provider matcher consistently.
  - QA scenarios: Happy - `uv run pytest tests/unit/application/utils/test_pr_url_parser.py tests/unit/infrastructure/test_input_validator.py tests/unit/infrastructure/test_gitlab_vcs_provider.py -v --tb=short`; Failure - table-driven attack/malformed URLs assert rejection and prove no encoded/traversal string reaches a fake `projects.get`. Evidence: `<attemptDir>/task-6-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `fix(gitlab): accept nested namespaces safely`.

- [x] 7. Preserve structured E5020 details at the raw FastMCP boundary
  - Recommended task executor category: `unspecified-high` - application-boundary behavior and protocol result shape require exact integration assertions without disturbing unrelated errors.
  - What to do: In the `get_pr_diff` handler in `prdiffer/application/tool_registry.py`, catch only `FullDiffIncompleteError`, record failure metrics once, and raise `fastmcp.exceptions.ToolError` whose compact JSON text is `{"error_code":"E5020_FULL_DIFF_INCOMPLETE","message":<error.message>,"details":<safe error.details>}`. Preserve optional `previous_path`, `observed`, and `limit`; keep deterministic key order. Add focused unit and raw `FastMCP.call_tool` tests.
  - Must NOT do: Do not catch/remap auth, permission, rate-limit, timeout, or unrelated exceptions in this branch; do not include `files`, raw contents, tokens, headers, traceback, or sanitized preview; do not change success serialization.
  - Parallelization: Wave 2 | Blocked by: 3 | Blocks: 16.
  - References: `prdiffer/application/tool_registry.py:237-329`; `prdiffer/domain/exceptions.py:255-357`; `tests/unit/application/test_tool_registry.py`; `tests/integration/test_full_diff_mcp_surface.py:122-141`; FastMCP error handling at `https://gofastmcp.com/servers/tools#error-handling`.
  - Acceptance criteria: Raw result has `isError is True`; parsing `content[0].text` yields exactly the three top-level keys; `error_code` is stable; details retain only E5020 safe fields; no `files` key exists anywhere; representative non-E5020 errors preserve their prior type/code path.
  - QA scenarios: Happy - call a fake GitLab reader that raises binary E5020 through `FastMCP.call_tool` and assert exact JSON fields; Failure - inject observed/limit/previous_path plus secret-like unrelated state and assert only the safe detail allowlist crosses. Run `uv run pytest tests/unit/application/test_tool_registry.py tests/integration/test_full_diff_mcp_surface.py -v --tb=short`. Evidence: `<attemptDir>/task-7-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `fix(mcp): preserve structured full-diff errors`.

- [ ] 8. Select one immutable GitLab MR diff version and capture a typed snapshot
  - Recommended task executor category: `deep` - correctness depends on reconciling two GitLab resource views without assuming list order or mutable endpoint stability.
  - What to do: Replace current head-SHA/current-`/diffs` acquisition in `prdiffer/infrastructure/vcs_providers/gitlab_operations.py`. Add boundary models in new `prdiffer/infrastructure/vcs_providers/gitlab_models.py`: `GitLabDiffRefs`, `GitLabVersionSummary`, `GitLabDiffRecord`, and frozen `GitLabDiffSnapshot` containing project path, IID, version ID, base/start/head SHAs, state, parsed real size, and ordered record tuple. Through todo 5's runtime: call `projects.get(unencoded_project_path)`, `project.mergerequests.get(iid)`, require complete MR `diff_refs`, list `mr.diffs.list(get_all=True)`, select exactly one summary whose three commit SHAs match those refs, fetch `mr.diffs.get(version_id)`, and revalidate the fetched version's ID/refs before snapshot construction.
  - Must NOT do: Do not select `versions[0]`, assume descending order, use head SHA alone, call `mr.diffs` current-file endpoint, retain the custom manual paging fallback, use `/changes`/`/raw_diffs`, or fall back when zero/multiple versions match.
  - Parallelization: Wave 3 | Blocked by: 3, 5 | Blocks: 9, 10, 11, 12.
  - References: `prdiffer/infrastructure/vcs_providers/gitlab_operations.py:28-94`; `tests/unit/infrastructure/test_gitlab_operations.py`; `tests/unit/infrastructure/test_gitlab_diff_pagination.py`; GitLab version endpoints at `https://docs.gitlab.com/api/merge_requests/#retrieve-merge-request-diff-versions`; python-gitlab pagination at `https://python-gitlab.readthedocs.io/en/stable/api-usage.html`.
  - Acceptance criteria: Exact one-match selection is independent of returned list order; the selected version is fetched by ID and its refs are rechecked; `projects.get` receives `group/subgroup/project` unencoded; zero/multiple match, missing/malformed refs, ID/ref drift, and malformed version payload fail E5020/`INVENTORY_TRUNCATED`; project/MR verified 404 map to E4001/E4002 instead.
  - QA scenarios: Happy - `uv run pytest tests/unit/infrastructure/test_gitlab_operations.py tests/unit/infrastructure/test_gitlab_diff_pagination.py -v --tb=short` with shuffled versions and one exact match; Failure - table-drive zero match, duplicate match, missing refs, fetched-version drift, 401/403/404/429/5xx and assert exact error family/code plus no current-diffs call. Evidence: `<attemptDir>/task-8-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `feat(gitlab): pin merge request diff version`.

- [x] 9. Admit a complete ordered GitLab inventory and classify every file state
  - Recommended task executor category: `unspecified-high` - authoritative cardinality, asynchronous states, and exhaustive flag/path/mode parsing are the core fail-closed contract.
  - What to do: In `gitlab_models.py` and `gitlab_operations.py`, parse the fetched version's embedded ordered `diffs`; require `state == "collected"` and decimal `real_size == len(diffs)`. Permit `state == "empty"` only when base SHA equals head SHA, embedded diffs are empty, and `real_size` is absent/zero; return a valid empty inventory. Reject `overflow`, `without_files`, deprecated timeout/overflow states, unknown/missing state, or nonempty ambiguous `empty` as E5020/`INVENTORY_TRUNCATED`. Enforce `config.max_files_allowed` before content retrieval. Preserve `old_path`, `new_path`, `a_mode`, `b_mode`, `new_file`, `deleted_file`, `renamed_file`, nullable `diff`, `collapsed`, `too_large`, and optional `generated_file`; exhaustively classify exactly one of added/deleted/renamed/modified and reject conflicting flags, missing required paths, path equality for rename, and malformed required modes as E5020/`UNSUPPORTED_FILE_STATUS`.
  - Must NOT do: Do not use MR `changes_count`, provider hunk presence, page length, `collapsed`, or `too_large` alone as completeness/cardinality proof; do not filter by GitHub ignore/extensions or reorder records. Suppressed/null patches remain recoverable metadata and proceed to raw content retrieval.
  - Parallelization: Wave 3 | Blocked by: 3, 5, 8 | Blocks: 11, 12, 15 | Can parallelize with: 10.
  - References: `prdiffer/infrastructure/vcs_providers/gitlab_operations.py:28-94`; `prdiffer/domain/exceptions.py:255-357`; `settings.toml:5,28-30`; GitLab diff limits at `https://docs.gitlab.com/administration/diff_limits/`; GitLab diff-version state model at `https://github.com/gitlabhq/gitlabhq/blob/master/app/models/merge_request_diff.rb`.
  - Acceptance criteria: Collected exact-size inventories and provably empty equal-ref snapshots succeed; all other states/cardinality mismatches fail before a content call; record order and flags/modes are byte-for-byte preserved; `observed` and `limit` are safe and meaningful for count/state failures; file count `max+1` maps to E5020/`FILE_COUNT_LIMIT`.
  - QA scenarios: Happy - `uv run pytest tests/unit/infrastructure/vcs_providers/test_gitlab_models.py tests/unit/infrastructure/test_gitlab_operations.py -v --tb=short` covers collected, empty, added/deleted/rename/mode-only, collapsed, too-large, null hunk, and generated records; Failure - overflow/without_files/unknown state, malformed real_size, count mismatch/limit, conflicting flags/path/mode errors each produce exact E5020 reason and zero content calls. Evidence: `<attemptDir>/task-9-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `feat(gitlab): fail closed on incomplete inventories`.

- [x] 10. Fetch typed old/new file content at immutable refs
  - Recommended task executor category: `unspecified-high` - provider I/O, typed availability, byte admission, decode, and status-specific ref/path rules must agree exactly.
  - What to do: Add `prdiffer/infrastructure/vcs_providers/gitlab_content.py` using todo 5's runtime and existing `FileContentAvailable | FileContentUnavailable`. For each admitted record use exact immutable refs: added fetches `new_path@head` and synthesizes available empty base; deleted fetches `old_path@base` and synthesizes available empty head; renamed fetches `old_path@base` plus `new_path@head`; modified/mode-only fetches old path at base plus new path at head. Use `project.files.raw(file_path=path, ref=sha)` through operation-scoped clients. Preserve indexed order with `AsyncParallelExecutor.execute_indexed_batch` (serialized capacity one when parallel fetch is disabled). Enforce byte size before UTF-8 decode; empty bytes are available `""`; NUL is binary; invalid UTF-8 is decode failure.
  - Must NOT do: Do not fetch an absent side for add/delete, use branch names/current refs, infer empty content from `diff is None`, cache unavailable results as success, or decode before byte-limit/NUL checks.
  - Parallelization: Wave 3 | Blocked by: 2, 3, 5, 8 | Blocks: 11, 12, 15 | Can parallelize with: 9.
  - References: `prdiffer/domain/entities/file_content.py`; `prdiffer/infrastructure/github/content_fetcher.py`; `prdiffer/infrastructure/utils/parallel/executor.py`; `prdiffer/infrastructure/vcs_providers/gitlab_repository.py:58-89`; GitLab raw-file API at `https://docs.gitlab.com/api/repository_files/#retrieve-a-raw-file-from-a-repository`.
  - Acceptance criteria: Every SDK call has the exact path/ref matrix above; output index count equals input count; empty bytes remain distinguishable from unavailable; required 404 yields E5020/`CONTENT_UNAVAILABLE` with path; oversize/NUL/decode failures map respectively to `FILE_SIZE_LIMIT`, `BINARY_CONTENT`, and `CONTENT_DECODE_FAILED`; timeout/auth/rate/5xx stay operational errors.
  - QA scenarios: Happy - `uv run pytest tests/unit/infrastructure/test_gitlab_file_content.py -v --tb=short` proves all four status matrices, zero-byte, generated, and parallel order; Failure - required 404, max+1 bytes, NUL, invalid UTF-8, worker failure, and index mismatch abort the whole batch with no successful partial tuple. Evidence: `<attemptDir>/task-10-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `feat(gitlab): load pinned typed file content`.

- [x] 11. Assemble ordered GitLab full-context file responses with strict size and state guarantees
  - Recommended task executor category: `deep` - this is the cohesive correctness seam joining inventory, typed contents, shared generation, status/stats mapping, and all-or-nothing limits.
  - What to do: Add `prdiffer/infrastructure/vcs_providers/gitlab_diff_generator.py`. Convert each admitted record plus typed contents into `FilePatchInfo` with provider patch deliberately excluded (`patch=""`), exact edit type, old path, and modes; call shared `DiffGenerator.generate_ordered_file_diffs`; verify one result per inventory index/path. Map to `FileDiffResponse` with provider status and rename `previous_path`. Compute additions/deletions only from generated unified lines (`+` excluding `+++`, `-` excluding `---`; rename/mode headers count zero). Permit empty textual diff only for an authoritatively zero-byte added/deleted file; require rename-only and mode-only headers; equal-content/equal-mode modified records fail E5020/`DIFF_GENERATION_FAILED`. Sum final diff character lengths and fail E5020/`RESPONSE_SIZE_LIMIT` before constructing `PRDiff` when `max_total_chars` is exceeded.
  - Must NOT do: Do not pass nullable/hunk-only provider text as output or fallback, trust provider additions/deletions, drop failed files, return a partial tuple, or emit `DIFF TRUNCATED`/binary notices.
  - Parallelization: Wave 3 | Blocked by: 3, 4, 8, 9, 10 | Blocks: 12, 15.
  - References: `prdiffer/domain/entities/file_patch.py`; `prdiffer/domain/entities/generated_file_diff.py`; `prdiffer/domain/entities/file_diff_response.py`; `prdiffer/infrastructure/github/diff_generator.py:60-231`; `prdiffer/infrastructure/services/pr_diff_service.py`; `tests/unit/infrastructure/github/test_generated_file_diffs.py`.
  - Acceptance criteria: Ordered multi-file output contains complete base/head context; add/delete/modified/rename/rename-only/mode-only/zero-byte stats and metadata are exact; `collapsed`, `too_large`, and null provider patches produce reconstructed full diffs when raw content is usable rather than false empty success; any unsupported/missing/index/size failure yields one E5020 and no PRDiff.
  - QA scenarios: Happy - `uv run pytest tests/unit/infrastructure/vcs_providers/test_gitlab_diff_generator.py -v --tb=short` with an ordered mixed-status fixture and capacities one/four; Failure - unknown status, equal no-op modified record, generated index/path mismatch, binary marker, and aggregate max+1 each fail with exact E5020 reason. Evidence: `<attemptDir>/task-11-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `feat(gitlab): generate strict full-context file responses`.

- [x] 12. Implement the request-scoped GitLab strict diff session
  - Recommended task executor category: `deep` - session lifecycle is the atomic unit binding snapshot, cache identity, inventory, content, assembler, deadlines, and cleanup.
  - What to do: Add `prdiffer/infrastructure/vcs_providers/gitlab_diff_session.py` implementing `PRDiffReadSessionInterface` and make `GitLabVCSRepository.open_pr_diff_session()` create it. Session open selects the immutable snapshot from todo 8 and exposes todo 1's GitLab cache identity. `build_pr_diff()` admits inventory, fetches contents, generates all responses, and may be called once; `aclose()` is idempotent, marks the session closed, releases request-scoped resources, and prevents further build. Preserve existing `supports_repository()`. For direct `PRDiffReader` compatibility, make `get_pr_diff()` delegate to open/build/finally-close and make `get_latest_commit_sha()` return the head from an independently opened/finally-closed session; the application strict path must use `open_pr_diff_session()` and never sequence those compatibility methods.
  - Must NOT do: Do not keep a mutable SDK MR/client on the session, re-read latest refs after open, reuse a closed session, return `None` for contract failures, or cache inside infrastructure.
  - Parallelization: Wave 4 | Blocked by: 1, 2, 3, 5, 8, 9, 10, 11 | Blocks: 13, 14, 15, 17.
  - References: `prdiffer/domain/interfaces/pr_diff_reader.py:16-55`; `prdiffer/infrastructure/github/pr_diff_session.py`; `prdiffer/infrastructure/vcs_providers/gitlab_repository.py:16-94`; `prdiffer/domain/interfaces/vcs_provider.py`; `tests/unit/infrastructure/github/test_pr_diff_session.py`.
  - Acceptance criteria: Opening performs snapshot selection once; cache identity matches exact snapshot; build uses only captured refs/version records; close executes after success or any E5020/operational failure and on cache-hit once integrated; second build/after-close use raises a deterministic lifecycle error without I/O.
  - QA scenarios: Happy - `uv run pytest tests/unit/infrastructure/vcs_providers/test_gitlab_diff_session.py tests/unit/infrastructure/test_gitlab_vcs_provider.py -v --tb=short` proves one open/build/close lifecycle; Failure - injected inventory/content/generator exceptions and cancellation each record one close and no partial result. Evidence: `<attemptDir>/task-12-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `feat(gitlab): add immutable full-diff session`.

- [ ] 13. Route GitLab through the generic strict session cache path and invalidate legacy cache behavior
  - Recommended task executor category: `deep` - cache read/write semantics and legacy fallback behavior must change without perturbing GitHub or non-session readers.
  - What to do: Refactor `_execute_session_path` in `prdiffer/domain/usecases/pr_diff_usecases.py` to consume `session.cache_identity.cache_key`, `.validation_token`, and `.schema_version` only; update `unwrap_pr_diff_cache_value` to validate against the identity and accept strict bare `PRDiff` values under exact GitHub-v2 or GitLab-v1 prefixes while rejecting legacy/wrong-schema data. In the session path ignore `cache_namespace`; retain it only for legacy cache keys. Keep `gitlab:` on the application coalescing key in `prdiffer/application/pr_diff_executor.py`, not on strict cache identity. Always close in `finally`, including optimistic/normal cache hits and failures. Replace `test_legacy_gitlab_path_unchanged` with a provider-neutral legacy fake; add GitLab session-path/cache migration tests.
  - Must NOT do: Do not inspect `snapshot.head_sha` or provider type in the use case, reuse `gitlab:<legacy-key>`, write E5020/partial results, change GitHub keys/validation tokens, or remove the legacy path for genuinely non-session readers.
  - Parallelization: Wave 4 | Blocked by: 1, 12 | Blocks: 14, 15, 16.
  - References: `prdiffer/domain/usecases/pr_diff_usecases.py:19-134`; `prdiffer/domain/entities/pr_diff_cache.py:1-46`; `prdiffer/application/pr_diff_executor.py:31-76`; `tests/unit/domain/usecases/test_session_pr_diff_usecase.py:1-131`; `tests/unit/domain/usecases/test_pr_diff_usecases.py`.
  - Acceptance criteria: GitLab cache hit needs zero content/generation calls and still closes; cache miss writes exact key/token and complete PRDiff only; legacy/wrong-version/wrong-token values miss; snapshot change changes key; GitHub and provider-neutral legacy tests are unchanged; E5020 never invokes cache `set`.
  - QA scenarios: Happy - `uv run pytest tests/unit/domain/test_gitlab_pr_diff_cache.py tests/unit/domain/usecases/test_session_pr_diff_usecase.py tests/unit/domain/usecases/test_pr_diff_usecases.py -v --tb=short`; Failure - preload legacy hunk, wrong schema, same-head/different-base version, and E5020 build, asserting all miss/fail safely and close exactly once. Evidence: `<attemptDir>/task-13-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `refactor(usecase): route strict readers by session identity`.

- [ ] 14. Compose the GitLab strict reader through settings, factory, and server wiring
  - Recommended task executor category: `unspecified-high` - multi-layer composition must preserve dependency direction and singleton resource ownership.
  - What to do: Add infrastructure factory methods in `prdiffer/infrastructure/factories/infrastructure_factory.py` for the shared GitLab limiter/runtime, operations, content adapter, generator, and strict repository/session reader. Update `prdiffer/server.py` to obtain the assembled GitLab reader from the infrastructure factory using the existing `GITLAB_TOKEN` source instead of direct `GitLabVCSRepository(...)`. Keep `ToolRegistry` typed to `PRDiffReader`/session protocols and pass the configured request deadline. Add factory singleton/transient and server composition tests.
  - Must NOT do: Do not import python-gitlab or concrete infrastructure into domain/application, create one limiter per request, change GitHub factory wiring, require a token for public-project behavior if current behavior permits empty token, or fix unrelated factory architecture debt.
  - Parallelization: Wave 4 | Blocked by: 2, 5, 6, 12, 13 | Blocks: 15, 16, 17.
  - References: `prdiffer/infrastructure/factories/infrastructure_factory.py`; `prdiffer/infrastructure/di_container.py`; `prdiffer/server.py:125-141`; `prdiffer/application/tool_registry.py:50-73`; `tests/unit/infrastructure/factories/test_infrastructure_factory.py`; `tests/unit/infrastructure/test_gitlab_config_wiring.py`.
  - Acceptance criteria: One limiter instance is shared across all sessions; SDK clients remain operation-scoped; server injects a session-capable GitLab reader; application/domain have no new outer-layer imports; the analyzer adds zero violations beyond the recorded application-factory baseline.
  - QA scenarios: Happy - `uv run pytest tests/unit/infrastructure/factories/test_infrastructure_factory.py tests/unit/test_server_gitlab_composition.py tests/unit/application/test_tool_registry.py -v --tb=short`; Failure - invalid config fails before registration, missing optional token preserves prior public behavior, and two created sessions share limiter but not SDK client objects. Evidence: `<attemptDir>/task-14-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `refactor(gitlab): compose strict reader through factory`.

- [ ] 15. Add a no-network GitLab strict full-diff integration state matrix
  - Recommended task executor category: `unspecified-high` - end-to-end provider/use-case/cache behavior needs realistic fake SDK managers rather than isolated mocks.
  - What to do: Add `tests/integration/test_gitlab_strict_full_diff.py` with a stateful fake python-gitlab project/MR/diff-version/file API and real domain use case, in-memory cache, runtime, session, content, generator, and repository. Cover ordered mixed files: modified, nonempty/empty add/delete, rename with content, rename-only, mode-only, generated, collapsed, too-large, and null provider patch. Cover immutable version selection under shuffled version order and target-ref refresh, legacy cache rejection, strict cache hit, provider coalescing namespace isolation, and close behavior.
  - Must NOT do: Do not call GitLab.com, mock the final `PRDiff`, assert implementation call trivia unrelated to contract, or preserve current tests that expect successful empty collapsed/too-large output.
  - Parallelization: Wave 5 | Blocked by: 6, 9, 10, 11, 12, 13, 14 | Blocks: 18, F1-F4 | Can parallelize with: 16, 17.
  - References: `tests/unit/infrastructure/test_gitlab_vcs_provider.py:84-145`; `tests/unit/infrastructure/test_gitlab_operations.py`; `tests/unit/infrastructure/test_gitlab_diff_pagination.py`; `tests/integration/test_complete_workflow.py`; all production modules from todos 5 and 8-14.
  - Acceptance criteria: Happy result has one response per inventory record in exact provider order, complete generated context, exact status/stats/previous_path/mode headers, and no provider hunk passthrough; every incomplete state yields no PRDiff and no cache write; same head with changed base/version cannot hit stale cache.
  - QA scenarios: Happy - `uv run pytest tests/integration/test_gitlab_strict_full_diff.py -v --tb=short -k 'success or cache or snapshot'`; Failure - run `-k 'incomplete or binary or oversized or decode or unavailable or conflict'` and assert exact E5020 reasons plus all-or-nothing cache/session state. Evidence: `<attemptDir>/task-15-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `test(gitlab): prove strict full-diff integration contract`.

- [ ] 16. Prove GitLab success and structured failures through the raw MCP protocol surface
  - Recommended task executor category: `unspecified-high` - public protocol behavior must be asserted after actual ToolRegistry registration and routing.
  - What to do: Strengthen `tests/integration/test_full_diff_mcp_surface.py` to register the real tool with a fake strict GitLab session reader and call `FastMCP.call_tool`. Success fixture uses a nested namespace and ordered rename/mode content. Failure fixture raises representative E5020 reasons and operational GitLab 401/403/429/5xx errors. Parse raw content instead of only checking that an exception occurred.
  - Must NOT do: Do not assert only prose substrings, use a GitHub target as a proxy for GitLab, accept `E5002_GITHUB_API_ERROR`, or expose `files` in an error result.
  - Parallelization: Wave 5 | Blocked by: 3, 6, 7, 13, 14 | Blocks: 18, F1-F4 | Can parallelize with: 15, 17.
  - References: `prdiffer/application/tool_registry.py:237-329`; `tests/integration/test_full_diff_mcp_surface.py:1-141`; `prdiffer/domain/entities/file_diff_response.py`; `prdiffer/domain/exceptions.py:255-357`.
  - Acceptance criteria: Raw success is `isError=false` and decodes to complete ordered files with rename `previous_path`; raw E5020 is `isError=true` and exact machine-readable code/details with no files; 401/403/429/5xx preserve E2006/E2007/E3006/E5021 and never become E4002/E5002/E5020; nested namespace routes to the GitLab reader once.
  - QA scenarios: Happy - `uv run pytest tests/integration/test_full_diff_mcp_surface.py -v --tb=short -k gitlab_success`; Failure - run the GitLab E5020 and operational-error parameter matrix and persist decoded raw results in evidence. Evidence: `<attemptDir>/task-16-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `test(mcp): assert GitLab raw full-diff contract`.

- [ ] 17. Add deterministic concurrency, deadline, and ordering performance regressions
  - Recommended task executor category: `unspecified-high` - resource behavior requires coordinated AnyIO tests and invariant-based evidence, not wall-clock benchmarks.
  - What to do: Add `tests/performance/test_gitlab_strict_full_diff.py` using AnyIO events/barriers and fake SDK operations. Run the same 50-file inventory with capacities one and four; record peak active operations, output identity/order, operation count, and deterministic completion. Add owner-deadline and per-call timeout scenarios with injected blocking events, plus transient retry attempt accounting and cancellation cleanup.
  - Must NOT do: Do not use `sleep`, flaky elapsed-time throughput thresholds, live network, modify GitHub's `scripts/bench_diff_generation.py`, or claim current unbounded memory behavior.
  - Parallelization: Wave 5 | Blocked by: 2, 5, 12, 14 | Blocks: 18, F1-F4 | Can parallelize with: 15, 16.
  - References: `prdiffer/infrastructure/utils/parallel/executor.py`; `prdiffer/application/pr_diff_executor.py:21-76`; `tests/performance`; `tests/unit/infrastructure/test_full_diff_concurrency_defaults.py`; `tests/unit/infrastructure/vcs_providers/test_gitlab_runtime.py` from todo 5.
  - Acceptance criteria: Peak active operations is exactly bounded by configured capacity; capacity one/four outputs are identical and ordered; injected owner timeout returns E5004 and closes operation-scoped clients; 5xx attempts never exceed configured total; 429 has no local duplicate retry; test is deterministic under repeated execution.
  - QA scenarios: Happy - invoke `uv run pytest tests/performance/test_gitlab_strict_full_diff.py -v --tb=short` three separate times and require identical assertions/order each run; Failure - hold the barrier past the injected deadline and assert E5004, zero cache write, one session close, and eventual worker-client cleanup. Evidence: `<attemptDir>/task-17-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `test(gitlab): lock concurrency deadline and ordering`.

- [ ] 18. Document the strict GitLab contract, configuration, and cache migration
  - Recommended task executor category: `writing` - public/operator documentation must mirror the verified behavior without changing implementation.
  - What to do: Update `README.md`, `settings.toml` comments, and `skills/prdiffer/SKILL.md` where GitLab/get_pr_diff behavior is described. State that GitLab success is immutable-version, generated full-context, ordered, all-or-nothing; list new `gitlab.*` settings under `[default]` and the nested namespace format; document that legacy GitLab hunk cache entries are ignored automatically; describe structured E5020 and provider-operational codes; state binary/oversized/unavailable files fail the whole request.
  - Must NOT do: Do not promise self-managed GitLab, raw diff endpoint support, partial output, live retry guarantees beyond configured SDK behavior, or change package version/release notes for an unreleased implementation.
  - Parallelization: Wave 5 | Blocked by: 15, 16, 17 | Blocks: F1-F4.
  - References: `README.md`; `settings.toml`; `skills/prdiffer/SKILL.md`; `prdiffer/application/tool_registry.py:240-253`; evidence from todos 15-17.
  - Acceptance criteria: Every documented field/default/error matches tested behavior; old hunk-only GitLab wording is removed; examples include one nested namespace; no unsupported provider/endpoint claim appears; documentation lint/basic hooks pass.
  - QA scenarios: Happy - run `uv run ruff check .` plus the repository's documentation/basic pre-commit hooks against changed docs/config; Failure - compare documented defaults/codes with executable config/error tests and fail if any literal differs. Evidence: `<attemptDir>/task-18-gitlab-strict-full-diff.txt`.
  - Commit: N | proposed `docs(gitlab): describe strict full-diff behavior`.

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit
  - Recommended task executor category: `unspecified-high` - trace every promised contract to implementation and evidence independently of implementer self-report.
  - What to verify: Read this plan and the final diff; build an 18-row compliance table with pass/fail and exact source/test/evidence reference for every todo. Re-run the focused cumulative pytest gate. Reject any missing failure branch, skipped evidence file, stale cache path, current `/diffs` call, partial-result path, or unverified structured transport field.
  - Acceptance: all 18 rows PASS; all referenced evidence exists and command output proves the named assertion ran; focused tests exit zero.
  - Evidence: `<attemptDir>/final-F1-gitlab-strict-full-diff.txt`.
- [ ] F2. Code quality review
  - Recommended task executor category: `deep` - review shared protocol changes, concurrency, error boundaries, type proofs, and module responsibility as one cohesive quality pass.
  - What to verify: Run `lsp_diagnostics` on every changed Python file, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, and the architecture analyzer. Measure pure LOC for every added/modified source module; reject any >250 without a justified `SIZE_OK`. Inspect for `Any` in public signatures, casts/ignores, broad/empty catches, blocking event-loop I/O, secret-bearing errors/logs, non-exhaustive tagged-state branches, duplicate retry loops, and mutable shared SDK clients.
  - Acceptance: diagnostics/lint/format/type pass; analyzer has no new violation beyond the recorded application-factory edge; no hard invariant or size defect remains.
  - Evidence: `<attemptDir>/final-F2-gitlab-strict-full-diff.txt`.
- [ ] F3. Real manual QA
  - Recommended task executor category: `unspecified-high` - exercise the actual registered MCP surface and async provider pipeline rather than internal functions alone.
  - What to verify: Through a no-network fake GitLab SDK and real `ToolRegistry`/`FastMCP.call_tool`, execute: nested-namespace ordered mixed-file success; collapsed/null-hunk reconstruction; cache miss then strict cache hit; binary E5020; inventory-size mismatch E5020; 401; 429; timeout. Capture decoded raw MCP success/error payloads. Then run `uv run pytest tests/integration/test_gitlab_strict_full_diff.py tests/integration/test_full_diff_mcp_surface.py tests/performance/test_gitlab_strict_full_diff.py -vv -s --tb=short`.
  - Acceptance: success is complete and ordered; every failure has exact nonpartial code/details; operational errors are not E5020/not-found; cache hit performs no content calls; all protocol/integration/performance scenarios pass.
  - Evidence: `<attemptDir>/final-F3-gitlab-strict-full-diff.txt` plus `<attemptDir>/final-F3-raw-success.json` and `<attemptDir>/final-F3-raw-errors.json`.
- [ ] F4. Scope fidelity
  - Recommended task executor category: `deep` - independently distinguish necessary shared seams from accidental provider or feature expansion.
  - What to verify: Inspect `git diff --name-status` and the complete patch against Must have/Must NOT have. Confirm no self-managed host/config, deprecated/raw diff endpoint, live-network test, partial mode, dependency/version bump, GitHub behavior drift, unrelated architecture cleanup, or secret exposure. Re-run GitHub cache/session/generator regressions and verify docs exactly match tested GitLab settings/codes.
  - Acceptance: every changed path maps to one todo; no out-of-scope behavior or dependency change exists; GitHub regression tests and `uv lock --check` pass; documentation and implementation constants agree.
  - Evidence: `<attemptDir>/final-F4-gitlab-strict-full-diff.txt`.

## Commit strategy
- The plan itself does not authorize commits. Every todo is marked `Commit: N`; execute without committing unless the user separately requests commits or starts work with a PR-producing mode.
- If commit authorization is present, create atomic commits only after each cumulative wave gate is green; never commit tests that expect behavior not present in the same commit and never mix unrelated user changes.
- Recommended authorized grouping: (1) strict cache/session contracts + GitLab config/errors/modes; (2) runtime + URL + MCP boundary; (3) immutable version/inventory/content/generation; (4) session/use-case/factory wiring; (5) integration/performance/docs. Use the proposed Conventional Commit subjects from the todos as the detailed commit body outline.
- Before any authorized commit, inspect `git status`, `git diff`, and recent log; stage only plan-owned files. No amend, force-push, or destructive reset.

## Success criteria
- A GitLab MR success is produced only from one fetched diff version whose version ID and base/start/head refs are immutable and exactly matched to the MR snapshot.
- Inventory cardinality/state is authoritative and ordered: collected exact-size or provably empty equal-ref only. Unknown, overflowed, without-files, mismatched, malformed, or over-limit inventory fails before content retrieval.
- Every admitted file is represented exactly once and in provider order. Modified, added, deleted, renamed, rename-only, zero-byte, generated, mode-only, collapsed, too-large, and nullable-provider-patch cases are reconstructed from pinned content or fail closed.
- No provider hunk is returned as the public full diff. Generated text contains complete context; rename/mode headers and additions/deletions are correct; binary, oversized, undecodable, unavailable, no-op-indeterminate, generation, and aggregate-limit failures yield exact E5020 reasons with no partial PRDiff/cache write.
- GitLab strict cache identity contains version ID plus all three refs; legacy GitLab hunk cache values and wrong schemas/tokens are ignored; GitHub v2 keys/output and non-session legacy reader behavior are unchanged; sessions close on hits, misses, errors, and cancellation.
- GitLab SDK work has explicit client timeout, bounded transient 5xx retries, SDK rate-limit obedience, a provider-shared limiter, operation-scoped clients, owner-deadline propagation, and deterministic cleanup. 401/403/404/429/5xx/timeout/connection failures map to the specified provider-aware codes and only verified 404 is not-found.
- Raw MCP success is non-error complete data; raw E5020 is `isError=true` compact JSON with `error_code`, `message`, safe `details`, and no `files`; other operational codes are not remapped.
- Canonical GitLab.com nested namespace URLs reach the same strict reader; malformed, traversal, encoded-separator, query/fragment, and self-managed URLs are rejected.
- Focused unit/integration/performance/raw-protocol tests, `uv lock --check`, Ruff lint/format, `ty`, the full pytest suite, and the architecture baseline all pass as specified; no source module exceeds 250 pure LOC without justified exemption.
- F1-F4 independently approve the same final worktree state and their evidence artifacts exist before the executor reports completion.
