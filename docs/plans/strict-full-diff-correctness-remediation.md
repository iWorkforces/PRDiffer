# strict-full-diff-correctness-remediation - Work Plan

## TL;DR (For humans)
**What you'll get:** GitHub and GitLab full-context diffs that are tied to one immutable provider snapshot, preserve exact regular-file, symlink, and submodule-link semantics, and never turn missing or failed work into an empty or partial success. Cache, cancellation, deadlines, statistics, and public error behavior are covered end to end.

**Why this approach:** The comparison identity and cache key change together, so a correct diff cannot be stored under an incomplete identity. Special Git objects are reconstructed from immutable tree/blob metadata, while operational and completeness failures remain explicitly separate and fail closed.

**What it will NOT do:** It will not change the public response shape, follow submodule repositories, add live-provider tests, migrate stale cache entries, or fold unrelated formatting and architecture cleanup into this work.

**Effort:** XL
**Risk:** High - immutable snapshot identity, exact Git rendering, and cancellation behavior cross provider, cache, concurrency, and public API boundaries.
**Decisions to sanity-check:** Hard cutover to a merge-base-plus-head cache identity; exact Git-style symlink and gitlink output; old entries are ignored rather than migrated; every fix is developed red-first.

Your next move: choose whether to start execution or run a high-accuracy plan review first. Full execution detail follows below.

---

> TL;DR (machine): XL/high-risk strict-diff remediation with immutable GitHub merge-base snapshots, cache v3, exact cross-provider Git objects, fail-closed provider/concurrency semantics, and full no-network release evidence.

## Scope
### Must have
- GitHub strict sessions capture and validate one immutable comparison: base-tip and head metadata are read, GitHub Compare resolves the merge-base, the authoritative changed-file count is strictly parsed, and the build uses the captured merge-base/head/count without rereading mutable fields.
- GitHub strict cache identity moves to `github-full-diff-v3:{owner}:{repo}:{pr}:{merge_base}:{head}` with a validation token containing the same immutable refs. Existing `PRDiffCacheEntryV2` value serialization remains unchanged; old `github-full-diff-v2` entries are ignored, never migrated.
- GitHub inventory/provider failures propagate as typed operational or E5020 failures and can never become `PRDiff(files=())`. Only a successfully materialized authoritative zero-file inventory may return and cache an empty result.
- GitHub and GitLab classify immutable tree entries before content acquisition. Mode `120000` uses the symlink blob itself; mode `160000` becomes canonical `Subproject commit <object-id>` text. Submodule repositories are never traversed.
- Shared full-context rendering preserves EOF/newline semantics, emits deterministic add/delete/change mode headers, and never falls back to provider hunks when exact reconstruction fails.
- The session-reader protocol accepts optional `base_url` on every implementation; the use case invokes it once, preserving custom GitLab hosts and allowing internal `TypeError` to propagate.
- Request coalescing has one canonical implementation, guarantees terminal publication on owner cancellation, releases waiters, removes pending state, and permits a later same-key request.
- GitLab content handling consumes `IndexedBatchError.first_failure`; GitHub enforces deadlines after non-abandoned worker completion; limiter capacity remains held until blocking SDK work actually exits.
- GitLab counts changed source lines beginning `++`/`--` correctly, rejects boolean `real_size`, and fail-closes incomplete SDK pagination. Malformed GitHub renames become E5020 before content acquisition.
- Add `FullDiffIncompleteReason.SNAPSHOT_CHANGED`, immutable snapshot revalidation, provider-level no-network integration coverage, registered FastMCP failure/cache coverage, and serial/parallel byte-equivalence coverage for both providers.
- Update user-facing strict-diff documentation and the shipped `prdiffer` skill for merge-base semantics, cache v3, special objects, snapshot drift, and stable E5020 behavior.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- No public fields added to `PRDiff`, `FileDiffResponse`, or MCP tool parameters. Provider object descriptors stay inside infrastructure and normalize into existing text/mode fields.
- No fallback to `pull_request.base.sha`, provider hunks, partial files, truncation notices, stale cache entries, or a newer provider snapshot.
- No automatic submodule-repository access, cross-repository token use, live-provider test, credential requirement, or network-dependent CI.
- No `abandon_on_cancel=True`, raw `asyncio`, sleeps in concurrency tests, broad error-to-empty conversion, or second failure-selection algorithm outside `IndexedBatchError.first_failure`.
- No cache-value schema bump, stale-key migration, compatibility shim, package-version bump, or new dependency unless execution proves the installed SDKs cannot call the documented REST surfaces.
- No unrelated formatting of the 12 known files, no remediation of the documented `application.factory -> infrastructure_factory` edge, and no approve/describe/tool redesign.
- No test-only production hooks, prose assertions, mock-only tautologies, weakened existing tests, type suppressions, or failing-test deletion.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: strict red -> green -> refactor TDD with `pytest`, AnyIO events/cancel scopes, stateful no-network provider fakes, local temporary Git repositories for golden diffs, in-process FastMCP calls, Ruff, ty, and the dependency analyzer.
- Every red phase records the focused command and the expected regression-specific failure before production edits. A test that fails from import/setup error is not accepted as red evidence.
- Every failure test asserts the exact exception class/code or E5020 reason, no partial `PRDiff`, no `files` member in MCP failure JSON, zero cache-set calls, exactly one `get_pr_diff` failure metric, and session/waiter/worker cleanup where applicable.
- Every success test asserts ordered paths, status, `previous_path`, exact UTF-8 diff bytes, stats, mode headers, cache identity/write count, and serial/parallel equivalence where applicable.
- No tests use credentials, external network, wall-clock sleeps, provider prose, or output derived from the implementation under test.
- Focused gate after each todo: run that todo's exact listed `uv run pytest ... -q` command, then `uv run ruff check` on its explicit production/test paths and `uv run ty check`.
- Interface/factory changes additionally run `python3 scripts/analyze_dependencies.py --path prdiffer`; the only acceptable reported violation is the documented existing application-factory edge.
- Before edits, capture and persist `BASELINE_SHA="$(git rev-parse HEAD)"` in the attempt evidence. Final changed-file formatting uses only the task-owned worktree diff: `git diff --name-only --diff-filter=ACMR "$BASELINE_SHA"...HEAD -- '*.py' | xargs uv run ruff format --check`. Whole-repository format drift is recorded but not modified.
- Full release gate: `uv run pytest tests -v --tb=short`, `uv run ruff check .`, `uv run ty check`, dependency analysis, registered FastMCP QA, and deterministic strict-diff benchmark coverage.
- Evidence: `<attemptDir>/task-<N>-strict-full-diff-correctness-remediation.txt` for each todo and `<attemptDir>/final-F<N>-strict-full-diff-correctness-remediation.md` for final verifiers (`attemptDir` is the current ULW attempt directory; outside ULW use `.omo/evidence/`).

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.
- **Wave 1 - contracts and primitives (Todos 1-5):** five disjoint owners establish immutable GitHub identity, canonical coalescing, exact diff rendering, GitLab stats, and strict GitLab `real_size` parsing.
- **Wave 2 - provider/session remediation (Todos 6-10):** after Wave 1 integration, five disjoint owners repair GitHub inventory errors, session host/deadline behavior, GitHub and GitLab object acquisition, and GitLab SDK pagination proof.
- **Wave 3 - composed provider and MCP proof (Todos 11-15):** provider integration, cross-provider parity, registered MCP failure semantics, and cache/no-write behavior run on separate test files and owners.
- **Wave 4 - adversarial hardening and docs (Todos 16-18):** snapshot mutation, cross-request concurrency, and documentation close the remaining proof gaps.
- Do not parallelize tasks that share a production or test file. Re-check ownership against the dependency matrix before dispatch; if a previous task expands its write set into another task's target, serialize those tasks and update the task ledger first.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | None | 6, 7, 8, 11, 15, 16 | 2, 3, 4, 5 |
| 2 | None | 7, 9, 14, 17 | 1, 3, 4, 5 |
| 3 | None | 8, 9, 11, 12, 13 | 1, 2, 4, 5 |
| 4 | None | 12, 13, 18 | 1, 2, 3, 5 |
| 5 | None | 10, 12, 18 | 1, 2, 3, 4 |
| 6 | 1 | 8, 11, 14, 15, 16 | 7, 9, 10 |
| 7 | 1, 2 | 11, 14, 17 | 6, 8, 9, 10 |
| 8 | 1, 3, 6 | 11, 13, 14, 16 | 7, 9, 10 |
| 9 | 2, 3 | 12, 13, 14, 17 | 6, 7, 8, 10 |
| 10 | 5 | 12, 14 | 6, 7, 8, 9 |
| 11 | 1, 3, 6, 7, 8 | 13, 14, 15, 16, 18 | 12 |
| 12 | 3, 4, 5, 9, 10 | 13, 14, 15, 18 | 11 |
| 13 | 11, 12 | 17, 18 | 14, 15 |
| 14 | 2, 7, 8, 9, 10, 11, 12 | 15, 17, 18 | 13 |
| 15 | 1, 6, 11, 12, 14 | 18 | 13 |
| 16 | 1, 6, 8, 11 | 18 | 17 |
| 17 | 2, 7, 9, 13, 14 | 18 | 16 |
| 18 | 4, 5, 11, 12, 13, 14, 15, 16, 17 | F1-F4 | None |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [ ] 1. Make the GitHub comparison snapshot and v3 cache identity atomic
  - What to do: write failing tests first, then replace `PRDiffSnapshot.base_sha` with explicit `base_tip_sha` and `merge_base_sha`; strictly validate nonempty 40/64-character hexadecimal SHAs and a non-boolean, nonnegative integer `changed_files`; resolve the merge base once with GitHub Compare using the captured base-tip and head SHAs; build `github-full-diff-v3` key/token from merge-base plus head; pass the snapshot into strict generation; re-fetch PR metadata and recompute merge-base/count after a build and raise new `FullDiffIncompleteReason.SNAPSHOT_CHANGED` on drift before the use case can cache the result.
  - What to do: keep `PRDiffCacheEntryV2` and `PRDIFF_CACHE_SCHEMA_V2` unchanged because the cached value shape does not change. Make `unwrap_pr_diff_cache_value` reject old GitHub v2 bare/wrapped entries for a v3 identity without migration. A changed base tip with unchanged merge-base/head must retain the same identity; changed merge-base with unchanged head must miss and rebuild.
  - Must NOT do: no base-tip fallback when Compare fails or omits `merge_base_commit.sha`; no cache read before merge-base acquisition; no retry against a newer snapshot; no GitLab cache-key change; no public DTO change.
  - Parallelization: Wave 1 | Blocked by: none | Blocks: 6, 7, 8, 11, 15, 16 | Exclusive owner: `prdiffer/domain/entities/pr_diff_cache.py`, `prdiffer/domain/exceptions.py`, `prdiffer/domain/interfaces/pr_diff_reader.py`, `prdiffer/infrastructure/github/pr_diff_session.py`, and the snapshot-related portions of `prdiffer/infrastructure/services/pr_diff_service.py`.
  - Recommended task executor category: `ultrabrain` - this is the one cohesive architecture task where snapshot semantics, provider comparison, cache validity, and post-build revalidation must be reasoned about together.
  - References: `prdiffer/domain/interfaces/pr_diff_reader.py:17-63`; `prdiffer/domain/entities/pr_diff_cache.py:9-133`; `prdiffer/domain/exceptions.py:273-375`; `prdiffer/infrastructure/github/pr_diff_session.py:35-227`; `prdiffer/infrastructure/services/pr_diff_service.py:390-513`; `prdiffer/infrastructure/github_repository.py::_get_merge_base_commits` as API-call precedent only, not its base-tip fallback; `prdiffer/infrastructure/vcs_providers/gitlab_diff_session.py:63-82` as immutable identity precedent; GitHub Compare contract: https://docs.github.com/en/rest/commits/commits#compare-two-commits.
  - Tests to add/update: `tests/unit/infrastructure/github/test_pr_diff_session.py`; `tests/unit/domain/entities/test_pr_diff_cache.py`; `tests/unit/domain/test_pr_diff_cache_v2.py`; `tests/unit/domain/usecases/test_session_pr_diff_usecase.py`; `tests/unit/domain/test_full_diff_incomplete_error.py`; snapshot-focused cases in `tests/unit/infrastructure/test_pr_diff_service_comprehensive.py`.
  - Acceptance criteria: same head/different merge-base yields distinct v3 key and token and two builds; changed base-tip/same merge-base/head hits once; v2 entries miss; Compare failure performs zero cache gets/sets; successful build revalidation matches head/merge-base/count; drift raises E5020 `SNAPSHOT_CHANGED`, closes the session, and performs zero cache sets; authoritative zero-file snapshot remains cacheable.
  - QA scenarios: happy - `uv run pytest tests/unit/infrastructure/github/test_pr_diff_session.py tests/unit/domain/entities/test_pr_diff_cache.py tests/unit/domain/test_pr_diff_cache_v2.py tests/unit/domain/usecases/test_session_pr_diff_usecase.py -q`; failure - `uv run pytest tests/unit/domain/test_full_diff_incomplete_error.py tests/unit/infrastructure/test_pr_diff_service_comprehensive.py -k 'merge_base or snapshot or cache' -q`. Record the confirmed red failure and green receipt in `<attemptDir>/task-1-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `fix(github): bind strict diff cache to immutable comparison`

- [ ] 2. Canonicalize request coalescing and guarantee cancellation cleanup
  - What to do: write event-driven cancellation tests first; retain `prdiffer/infrastructure/utils/coalescing_service.py` as the only implementation; convert `prdiffer/infrastructure/utils/coalescing/service.py` and `coalescing/__init__.py` to pure re-exports following the circuit-breaker shim pattern. In shielded in-memory cleanup, publish the terminal cancellation, signal the event, remove the exact owner entry under the lock, then re-raise owner cancellation. Waiters must terminate rather than time out, waiter counts must not underflow, and a later same-key owner must execute normally.
  - Must NOT do: do not duplicate the state machine, swallow owner cancellation, leave an event unsignaled, use `asyncio`, use sleeps, or change provider worker abandonment behavior.
  - Parallelization: Wave 1 | Blocked by: none | Blocks: 7, 9, 14, 17 | Exclusive owner: both coalescer module paths, `coalescing/__init__.py`, and both coalescer test modules.
  - Recommended task executor category: `deep` - AnyIO cancellation, shielded terminal publication, and waiter/owner races require concurrency-focused implementation and proof.
  - References: `prdiffer/infrastructure/utils/coalescing_service.py:18-221`; `prdiffer/infrastructure/utils/coalescing/service.py:18-216`; `prdiffer/infrastructure/utils/coalescing/__init__.py`; `prdiffer/infrastructure/utils/circuit_breaker/core.py` re-export precedent; `prdiffer/application/pr_diff_executor.py:31-84`; `prdiffer/domain/interfaces/request_coalescing.py:11-45`.
  - Tests to add/update: `tests/unit/infrastructure/utils/test_coalescing.py`; `tests/unit/infrastructure/test_request_coalescing.py`.
  - Acceptance criteria: flat/package class and singleton getter identities are identical; owner cancellation after a waiter joins terminates owner and waiter, reports zero pending keys/waiters, and allows a new same-key request; success still performs one fetch for all waiters; ordinary failure reaches all waiters and leaves clean stats.
  - QA scenarios: happy - `uv run pytest tests/unit/infrastructure/utils/test_coalescing.py tests/unit/infrastructure/test_request_coalescing.py -k 'success or coalesc' -q`; failure - `uv run pytest tests/unit/infrastructure/utils/test_coalescing.py tests/unit/infrastructure/test_request_coalescing.py -k 'cancel or cleanup or import' -q`. Use AnyIO events/barriers and record `<attemptDir>/task-2-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `fix(concurrency): clean cancelled coalesced owners`

- [ ] 3. Make full-context rendering exact for modes and EOF semantics
  - What to do: lock current regular-file output, then make `DiffUtils` preserve final-newline state and emit `\ No newline at end of file` markers exactly; extend `DiffGenerator` to emit deterministic `new file mode`, `deleted file mode`, or `old mode`/`new mode` headers for 100644/100755/120000/160000; preserve header order as mode, rename, then body; reject reconstruction failures rather than returning the provider patch. Cover added/deleted/modified symlinks and gitlinks using no-network local Git-derived golden output.
  - Must NOT do: no provider-hunk fallback, no whole public DTO redesign, no binary sentinel success, no unrelated diff algorithm rewrite, and no regular-file output changes unless required for correct EOF markers and locked by tests.
  - Parallelization: Wave 1 | Blocked by: none | Blocks: 8, 9, 11, 12, 13 | Exclusive owner: `prdiffer/infrastructure/utils/diff_utils.py`, `prdiffer/infrastructure/github/diff_generator.py`, their domain protocol if needed, and renderer tests.
  - Recommended task executor category: `deep` - exact unified-diff byte semantics and mode/header ordering cross the shared renderer used by both providers.
  - References: `prdiffer/infrastructure/utils/diff_utils.py:40-225`; `prdiffer/infrastructure/github/diff_generator.py:60-203`; `prdiffer/domain/services/diff.py:11-53`; `prdiffer/domain/entities/file_patch.py` mode fields; `tests/unit/infrastructure/utils/test_diff_utils.py`; `tests/test_phase2_improvements.py`; Git tree mode contract: https://docs.github.com/en/rest/git/trees#create-a-tree.
  - Tests to add/update: `tests/unit/infrastructure/utils/test_diff_utils.py`; `tests/unit/infrastructure/github/test_diff_generator.py`; `tests/unit/infrastructure/github/test_diff_generator_comprehensive.py`; add a focused temporary-local-Git golden test module if existing files would mix responsibilities.
  - Acceptance criteria: final newline present/absent on either side produces exact markers; add/delete/change mode headers match Git-style output; symlink target and `Subproject commit <sha>` lines diff as ordinary canonical text; rename/mode/header order is fixed; a forced renderer exception raises typed E5003/E5020 and never returns provider hunk text; prior regular full-context fixtures remain byte-identical except corrected EOF cases.
  - QA scenarios: happy - `uv run pytest tests/unit/infrastructure/utils/test_diff_utils.py tests/unit/infrastructure/github/test_diff_generator.py tests/test_phase2_improvements.py -q`; failure - `uv run pytest tests/unit/infrastructure/github/test_diff_generator_comprehensive.py -k 'mode or newline or fallback or gitlink or symlink' -q`. Record local-Git command/output and test receipt in `<attemptDir>/task-3-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `fix(diff): preserve git mode and eof semantics`

- [ ] 4. Count GitLab unified-diff statistics by hunk state
  - What to do: write the `--old` to `++new` regression first, then replace broad `startswith("+++")`/`startswith("---")` exclusion with a narrow state machine that counts `+`/`-` only inside `@@` hunks. Actual file headers before a hunk remain excluded; source lines whose payload starts with `++` or `--` count normally.
  - Must NOT do: do not redesign general patch parsing, alter generated diff text, or infer stats from provider metadata.
  - Parallelization: Wave 1 | Blocked by: none | Blocks: 12, 13, 18 | Exclusive owner: `prdiffer/infrastructure/vcs_providers/gitlab_diff_generator.py` and its unit tests.
  - Recommended task executor category: `quick` - one pure parser and a compact regression matrix.
  - References: `prdiffer/infrastructure/vcs_providers/gitlab_diff_generator.py:117-149`; `tests/unit/infrastructure/vcs_providers/test_gitlab_diff_generator.py`.
  - Acceptance criteria: `--old` to `++new` reports one deletion and one addition; real `--- a/path`/`+++ b/path` headers report zero; context, `\ No newline...`, mode, and rename metadata do not affect counts; existing status/stat tests stay green.
  - QA scenarios: happy/failure - `uv run pytest tests/unit/infrastructure/vcs_providers/test_gitlab_diff_generator.py -k 'stats or plus or minus or header' -q`. Record red/green output in `<attemptDir>/task-4-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `fix(gitlab): count prefixed source lines correctly`

- [ ] 5. Parse GitLab diff-version `real_size` without boolean coercion
  - What to do: add boundary tests, then accept only a nonnegative non-boolean integer or an explicitly supported decimal string; reject booleans, floats, negative values, empty/malformed strings, and other types before inventory admission. Preserve exact version-ID and base/start/head revalidation.
  - Must NOT do: no general provider metadata coercion refactor and no change to conforming GitLab version semantics.
  - Parallelization: Wave 1 | Blocked by: none | Blocks: 10, 12, 18 | Exclusive owner: `prdiffer/infrastructure/vcs_providers/gitlab_operations.py` and `real_size` parser tests; touch `gitlab_inventory.py` only if duplicated acceptance remains after parser correction.
  - Recommended task executor category: `quick` - a strict boundary parse with a small table-driven test.
  - References: `prdiffer/infrastructure/vcs_providers/gitlab_operations.py:145-212`; `prdiffer/infrastructure/vcs_providers/gitlab_inventory.py:170-182`; `tests/unit/infrastructure/test_gitlab_operations.py`; GitLab diff-version contract: https://docs.gitlab.com/api/merge_requests/#get-a-single-merge-request-diff-version.
  - Acceptance criteria: `True` no longer equals one; valid `1` and supported `"1"` succeed; malformed values fail closed with the chosen existing inventory E5020 reason; fetched version/ref validation and record cardinality remain unchanged.
  - QA scenarios: happy/failure - `uv run pytest tests/unit/infrastructure/test_gitlab_operations.py -k 'real_size or version or inventory' -q`. Record the table and receipt in `<attemptDir>/task-5-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `fix(gitlab): reject invalid diff version sizes`

- [ ] 6. Propagate GitHub inventory and provider failures without false emptiness
  - What to do: write a stateful page-two failure test first; pass `snapshot.authoritative_changed_files` into `prepare_selected_inventory`; materialize every page before filtering; remove broad exception-to-`[]` conversion from the active session build; preserve existing domain exceptions, map PyGithub failures through the current infrastructure error boundary, and reserve E5020 for deterministic incompleteness such as enumerated-count mismatch. Only captured count zero plus a successfully exhausted empty iterator may build/cache `PRDiff(files=())`.
  - Must NOT do: no raw PyGithub exception leakage through MCP, no operational failure reclassified as E5020, no partial page success, and no blanket rejection of legitimate zero-file snapshots.
  - Parallelization: Wave 2 | Blocked by: 1 | Blocks: 8, 11, 14, 15, 16 | Exclusive owner: `prdiffer/infrastructure/services/pr_diff_service.py`, `prdiffer/infrastructure/github/inventory.py`, and service/inventory regression tests.
  - Recommended task executor category: `deep` - this must preserve the operational error taxonomy while eliminating a critical cached false-success path.
  - References: `prdiffer/infrastructure/services/pr_diff_service.py:390-493`; `prdiffer/infrastructure/github/inventory.py:26-130`; `prdiffer/domain/usecases/pr_diff_usecases.py:92-114`; `prdiffer/domain/exceptions.py::wrap_github_exception`; GitHub PR-file pagination/3,000 cap: https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files.
  - Tests to add/update: `tests/unit/infrastructure/test_pr_diff_service_comprehensive.py`; `tests/unit/infrastructure/test_pr_diff_service_full_context.py`; `tests/unit/infrastructure/github/test_inventory_admission.py`; no-cache assertion in `tests/unit/domain/usecases/test_session_pr_diff_usecase.py` only if not already covered by Todo 1.
  - Acceptance criteria: iterator yields page one then raises on page two -> mapped failure, zero public files, zero cache sets; full iterator/count mismatch -> E5020 `INVENTORY_TRUNCATED`; count zero/exhausted empty -> successful cached empty result; ignored-file filtering cannot hide a missing page; 3,000+ authoritative count fails before content calls.
  - QA scenarios: happy - `uv run pytest tests/unit/infrastructure/github/test_inventory_admission.py -k 'empty or complete or order' -q`; failure - `uv run pytest tests/unit/infrastructure/test_pr_diff_service_comprehensive.py tests/unit/infrastructure/test_pr_diff_service_full_context.py -k 'pagination or provider or inventory or cache' -q`. Record `<attemptDir>/task-6-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `fix(github): fail closed on incomplete provider inventory`

- [ ] 7. Make session host dispatch explicit and enforce post-worker deadlines
  - What to do: write one-call custom-host and late-worker tests first; change `SessionPRDiffReader.open_pr_diff_session` and both provider implementations to accept `*, base_url: str | None = None`; make `GetPRDiffUseCase` call it exactly once with no `inspect.signature` or `TypeError` fallback. GitHub receives `None`; GitLab preserves the validated URL. Add post-worker `_ensure_budget()` checks after GitHub session-open and build workers, while retaining `abandon_on_cancel=False` and limiter ownership until worker exit.
  - Must NOT do: no host defaulting after invocation, no internal `TypeError` retry, no cancellation of the blocking thread, and no capacity release before worker completion.
  - Parallelization: Wave 2 | Blocked by: 1, 2 | Blocks: 11, 14, 17 | Exclusive owner: `prdiffer/domain/interfaces/pr_diff_reader.py`, `prdiffer/domain/usecases/pr_diff_usecases.py`, `prdiffer/infrastructure/github/pr_diff_session.py`, `prdiffer/infrastructure/vcs_providers/gitlab_diff_session.py`, and their session/use-case tests.
  - Recommended task executor category: `deep` - protocol migration, host isolation, AnyIO thread semantics, and deterministic budget testing are coupled.
  - References: `prdiffer/domain/interfaces/pr_diff_reader.py:51-63`; `prdiffer/domain/usecases/pr_diff_usecases.py:67-114`; `prdiffer/infrastructure/github/pr_diff_session.py:75-113,160-227`; `prdiffer/infrastructure/vcs_providers/gitlab_diff_session.py:151-194`; `prdiffer/infrastructure/vcs_providers/gitlab_runtime.py:313-387` as the post-worker model.
  - Tests to add/update: `tests/unit/domain/usecases/test_session_pr_diff_usecase.py`; `tests/unit/infrastructure/github/test_pr_diff_session.py`; `tests/unit/infrastructure/vcs_providers/test_gitlab_diff_session.py`; `tests/unit/infrastructure/vcs_providers/test_gitlab_runtime.py` for capacity precedent only.
  - Acceptance criteria: custom-host internal `TypeError` records one call with the original URL and zero cache sets; GitHub is called once with `None`; late open/build worker raises E5004 after return; capacity-one test proves a second worker cannot enter until the first exits; early result succeeds; all opened sessions close.
  - QA scenarios: happy - `uv run pytest tests/unit/domain/usecases/test_session_pr_diff_usecase.py tests/unit/infrastructure/vcs_providers/test_gitlab_diff_session.py -k 'base_url or session or close' -q`; failure - `uv run pytest tests/unit/infrastructure/github/test_pr_diff_session.py -k 'deadline or limiter or cancel' -q`. Use patched monotonic time and events, never sleep; record `<attemptDir>/task-7-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `fix(session): preserve provider host and reject late workers`

- [ ] 8. Add immutable GitHub tree/object acquisition and reject malformed renames
  - What to do: add a focused `prdiffer/infrastructure/github/git_objects.py` (or equivalently narrow module under 250 pure LOC) with frozen typed descriptors for path, ref, six-digit mode, object type, and object ID; load recursive merge-base/head trees by immutable SHA and reject `truncated`; cross-check every required old/new selected path. Use Contents only for tree-proven regular blobs and verify returned SHA; fetch mode-120000 blob bytes by object ID; synthesize mode-160000 text as `Subproject commit <sha>\n`; reject NUL, invalid UTF-8, size excess, missing/ambiguous/malformed entries with the mapped E5020 reasons. Reject a rename lacking a distinct `previous_filename` before any tree/content call.
  - What to do: normalize exact object payload and modes into `FilePatchInfo`; introduce one frozen build-context value object rather than adding more processor parameters; keep the public DTO and shared text cache key `(repository,path,ref)` unchanged.
  - Must NOT do: no symlink target following, no submodule repository access, no `FileContentAvailable` public/shared-model widening solely for GitHub descriptors, no new lines added to the existing oversized client module when extraction into the new object module is possible, and no fallback from missing old rename path to the new path.
  - Parallelization: Wave 2 | Blocked by: 1, 3, 6 | Blocks: 11, 13, 14, 16 | Exclusive owner: new GitHub object module, `prdiffer/infrastructure/github/client_operations.py`, `prdiffer/infrastructure/github/file_processor.py`, and GitHub object/content/processor tests.
  - Recommended task executor category: `deep` - immutable tree classification, blob retrieval, status-specific old/new identity, and exact special-object normalization form one provider boundary.
  - References: `prdiffer/infrastructure/github/client_operations.py:180-435`; `prdiffer/infrastructure/github/file_processor.py:109-315`; `prdiffer/domain/entities/file_content.py:14-57`; `prdiffer/domain/entities/file_patch.py`; `prdiffer/infrastructure/github/inventory.py`; GitHub Contents semantics: https://docs.github.com/en/rest/repos/contents#get-repository-content; blob API: https://docs.github.com/en/rest/git/blobs#get-a-blob; tree API: https://docs.github.com/en/rest/git/trees#get-a-tree.
  - Tests to add/update: new `tests/unit/infrastructure/github/test_git_objects.py`; `tests/unit/infrastructure/github/test_file_content_typed.py`; `tests/unit/infrastructure/github/test_file_content_multi_ref_batch.py`; `tests/unit/infrastructure/github/test_file_processor_ordered.py`; `tests/unit/infrastructure/github/test_file_processor_comprehensive.py`.
  - Acceptance criteria: regular zero-byte file remains available; regular NUL/invalid UTF-8/oversize fails with `BINARY_CONTENT`/`CONTENT_DECODE_FAILED`/`FILE_SIZE_LIMIT`; symlink diffs its blob target bytes; gitlink emits canonical commit text without content API call; truncated tree is `INVENTORY_TRUNCATED`; missing selected object is `CONTENT_UNAVAILABLE`; malformed mode/type/id or rename is `UNSUPPORTED_FILE_STATUS`; all failures produce zero partial patches and zero successful content-cache entries.
  - QA scenarios: happy - `uv run pytest tests/unit/infrastructure/github/test_git_objects.py tests/unit/infrastructure/github/test_file_content_typed.py tests/unit/infrastructure/github/test_file_processor_ordered.py -q`; failure - `uv run pytest tests/unit/infrastructure/github/test_file_content_multi_ref_batch.py tests/unit/infrastructure/github/test_file_processor_comprehensive.py -k 'binary or symlink or gitlink or rename or truncated or missing' -q`. Record `<attemptDir>/task-8-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `fix(github): preserve immutable git object semantics`

- [ ] 9. Add immutable GitLab object acquisition and preserve indexed root failures
  - What to do: add a narrow GitLab object-descriptor module and tree loader under `GitLabRuntime.run_blocking`; fetch complete immutable base/head trees with `get_all=True`, cross-check inventory paths/modes/types/IDs, fetch mode-120000 blobs by object ID, synthesize mode-160000 commit text, and use `project.files.raw` only for tree-proven regular blobs. In `GitLabContentFetcher.fetch_all`, consume only `IndexedBatchError.first_failure`; preserve stable indexed ordering and non-cancellation root identity.
  - Must NOT do: no raw-file call for gitlinks/symlinks, no submodule traversal, no provider-hunk content source, no duplicate root-failure algorithm, and no partial content tuple after any indexed failure.
  - Parallelization: Wave 2 | Blocked by: 2, 3 | Blocks: 12, 13, 14, 17 | Exclusive owner: new GitLab object module, `prdiffer/infrastructure/vcs_providers/gitlab_content.py`, directly required GitLab model/inventory fields, and GitLab content/object tests.
  - Recommended task executor category: `deep` - provider object semantics and cancellation-aware indexed unwrapping share the same content boundary and file ownership.
  - References: `prdiffer/infrastructure/vcs_providers/gitlab_content.py:28-281`; `prdiffer/infrastructure/vcs_providers/gitlab_models.py:9-125`; `prdiffer/infrastructure/vcs_providers/gitlab_inventory.py:27-198`; `prdiffer/infrastructure/utils/parallel/results.py:55-127`; `prdiffer/infrastructure/utils/parallel/executor.py:407-535`; GitLab tree API: https://docs.gitlab.com/api/repositories#list-all-repository-trees-in-a-project; raw blob API: https://docs.gitlab.com/api/repositories#retrieve-raw-blob-content; raw file limitation: https://docs.gitlab.com/api/repository_files#retrieve-a-raw-file-from-a-repository.
  - Tests to add/update: new `tests/unit/infrastructure/vcs_providers/test_gitlab_objects.py`; `tests/unit/infrastructure/test_gitlab_file_content.py`; `tests/unit/infrastructure/test_async_parallel_executor.py`; `tests/unit/infrastructure/vcs_providers/test_gitlab_diff_generator.py` for normalized special-object assembly only.
  - Acceptance criteria: regular files still use exact base/head raw refs; symlink and gitlink never call raw-file API; tree truncation/mismatch fails E5020; index-0 cancellation plus index-1 E5020/`ValueError` surfaces the non-cancellation root; multiple real failures select the lowest stable index; all-cancellation preserves cancellation; serial/parallel ordering and no-partial behavior stay intact.
  - QA scenarios: happy - `uv run pytest tests/unit/infrastructure/vcs_providers/test_gitlab_objects.py tests/unit/infrastructure/test_gitlab_file_content.py -k 'regular or symlink or gitlink or order' -q`; failure - `uv run pytest tests/unit/infrastructure/test_async_parallel_executor.py tests/unit/infrastructure/test_gitlab_file_content.py -k 'cancel or first_failure or truncated or missing' -q`. Record `<attemptDir>/task-9-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `fix(gitlab): preserve git objects and indexed root failures`

- [ ] 10. Prove GitLab diff-version pagination failures cannot create a snapshot
  - What to do: add a stateful python-gitlab adapter fake whose `diffs.list(get_all=True)` exposes an earlier page and fails while materializing a later page; exercise exact version selection and session open. Assert the provider failure propagates through the existing mapped operational path, no partial `GitLabDiffSnapshot` exists, and later integration tasks can observe zero cache writes.
  - Must NOT do: no live GitLab request, no fake that fails before pagination starts, no production edit in this proof-only task, and no reinterpretation of provider errors as E5020 inventory mismatch. If the proof fails, reopen the owning Todo 5 boundary instead of editing production here.
  - Parallelization: Wave 2 | Blocked by: 5 | Blocks: 12, 14 | Exclusive owner: pagination cases in `tests/unit/infrastructure/test_gitlab_operations.py` and `tests/unit/infrastructure/test_gitlab_diff_pagination.py`.
  - Recommended task executor category: `quick` - this closes a bounded SDK-adapter proof gap with stateful fakes.
  - References: `prdiffer/infrastructure/vcs_providers/gitlab_operations.py:145-199`; `tests/unit/infrastructure/test_gitlab_operations.py`; `tests/unit/infrastructure/test_gitlab_diff_pagination.py`; GitLab diff versions: https://docs.gitlab.com/api/merge_requests/#list-merge-request-diff-versions.
  - Acceptance criteria: `get_all=True` is asserted; later-page failure returns no selected/fetched version and no snapshot; successful multi-page unordered input still selects exactly one three-ref match by ID and revalidates fetched refs; zero/multiple matches remain E5020 `INVENTORY_TRUNCATED` rather than operational pagination errors.
  - QA scenarios: happy/failure - `uv run pytest tests/unit/infrastructure/test_gitlab_operations.py tests/unit/infrastructure/test_gitlab_diff_pagination.py -k 'pagination or page or exact_version' -q`. Record `<attemptDir>/task-10-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `test(gitlab): prove diff version pagination fails closed`

- [ ] 11. Build a no-network GitHub strict-pipeline integration matrix
  - What to do: add `tests/integration/test_github_strict_full_diff.py` using the real session reader, use case, recording cache, FileProcessor, DiffGenerator, and GitHub service around a stateful fake PyGithub client/repository/PR. Exercise modified/added/deleted/renamed, zero-byte, mode-only, symlink, gitlink, complete pagination, legitimate zero-file cache, v3 miss/hit, page failure, object failure, deadline failure, and snapshot revalidation.
  - Must NOT do: no direct return of expected `PRDiff` from the fake, no network/client construction, no duplicated production logic in fixtures, and no assertion limited to method calls when returned bytes/cache/error state are observable.
  - Parallelization: Wave 3 | Blocked by: 1, 3, 6, 7, 8 | Blocks: 13, 14, 15, 16, 18 | Can parallelize with: 12 | Exclusive owner: new GitHub integration module and its focused helpers.
  - Recommended task executor category: `unspecified-high` - standard multi-layer integration with stateful provider fakes and real strict components.
  - References: `prdiffer/infrastructure/github/pr_diff_session.py`; `prdiffer/infrastructure/services/pr_diff_service.py`; `prdiffer/infrastructure/github/file_processor.py`; `prdiffer/infrastructure/github/diff_generator.py`; `prdiffer/domain/usecases/pr_diff_usecases.py`; fixture patterns in `tests/conftest.py`, `tests/integration/test_gitlab_strict_full_diff.py`, and `tests/integration/test_full_diff_mcp_surface.py`.
  - Acceptance criteria: success returns one ordered response per selected file with exact status/path/previous_path/modes/diff/stats; cache hit performs zero compare/inventory/content/generation work after session identity acquisition; every deterministic incompleteness has exact E5020 reason and zero cache sets; every operational failure retains its non-E5020 code; all sessions close once; no fake network path is reachable.
  - QA scenarios: happy - `uv run pytest tests/integration/test_github_strict_full_diff.py -k 'success or zero_file or cache_hit' -q`; failure - `uv run pytest tests/integration/test_github_strict_full_diff.py -k 'failure or pagination or object or drift or deadline' -q`. Persist representative public objects/errors in `<attemptDir>/task-11-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `test(github): cover strict pipeline end to end`

- [ ] 12. Extend the no-network GitLab strict-pipeline integration matrix
  - What to do: extend `tests/integration/test_gitlab_strict_full_diff.py` with real object loader/content fetcher/assembler/session/use-case wiring and stateful fake SDK operations. Add symlink/gitlink, `++`/`--` stats, strict `real_size`, later-page failure, cancellation-plus-root-failure, cache hit/miss, and no-write cases while retaining existing exact-version/base/start/head coverage.
  - Must NOT do: no provider hunk output, raw-file request for modes 120000/160000, live SDK client, or broad rewrite of the established GitLab integration fixture.
  - Parallelization: Wave 3 | Blocked by: 3, 4, 5, 9, 10 | Blocks: 13, 14, 15, 18 | Can parallelize with: 11 | Exclusive owner: `tests/integration/test_gitlab_strict_full_diff.py` during this wave.
  - Recommended task executor category: `unspecified-high` - multi-component provider integration on an existing mature fixture.
  - References: `prdiffer/infrastructure/vcs_providers/gitlab_diff_session.py`; `gitlab_operations.py`; `gitlab_inventory.py`; `gitlab_content.py`; `gitlab_diff_generator.py`; `tests/integration/test_gitlab_strict_full_diff.py`; `tests/performance/test_gitlab_strict_full_diff.py`.
  - Acceptance criteria: exact pinned snapshot and cache identity remain unchanged; regular/symlink/gitlink status matrix produces canonical ordered full-context output; real stats are exact; later-page/provider failure yields no snapshot/cache write; indexed root failure is non-cancellation when present; every failure closes the session and returns no partial `PRDiff`.
  - QA scenarios: happy - `uv run pytest tests/integration/test_gitlab_strict_full_diff.py -k 'success or cache or symlink or gitlink or stats' -q`; failure - `uv run pytest tests/integration/test_gitlab_strict_full_diff.py -k 'failure or pagination or cancel or binary or incomplete' -q`. Record `<attemptDir>/task-12-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `test(gitlab): extend strict object and failure coverage`

- [ ] 13. Prove serial and parallel public outputs are byte-equivalent
  - What to do: add `tests/integration/test_strict_full_diff_parity.py`. For each provider, run one deterministic mixed fixture with all relevant parallel flags off and on: added, modified, deleted, renamed, mode-only, zero-byte, symlink, gitlink, and source lines beginning `++`/`--`. Compare `PRDiff` equality and canonical bytes built independently with `dataclasses.asdict` plus deterministic JSON separators; separately compare every `diff.encode("utf-8")`. Add a failure fixture with a delayed sibling and one root failure.
  - Must NOT do: no set-based comparison, completion-order normalization, implementation-derived expected values, performance timing assertion, or silent difference in error reason/details.
  - Parallelization: Wave 3 | Blocked by: 11, 12 | Blocks: 17, 18 | Can parallelize with: 14, 15 | Exclusive owner: new parity integration module.
  - Recommended task executor category: `deep` - cross-provider concurrency equivalence must distinguish byte, order, identity, and failure semantics.
  - References: `prdiffer/infrastructure/github/file_processor.py`; `prdiffer/infrastructure/github/diff_generator.py`; `prdiffer/infrastructure/utils/parallel/executor.py`; `prdiffer/infrastructure/vcs_providers/gitlab_content.py`; `prdiffer/infrastructure/vcs_providers/gitlab_diff_generator.py`; `tests/performance/test_full_diff_benchmark.py` for deterministic workload patterns only.
  - Acceptance criteria: serial/parallel canonical bytes, file order, previous paths, modes, newline markers, stats, and cacheability are identical for each provider; failure class/code/reason/details are identical; neither mode returns partial files or writes cache on failure.
  - QA scenarios: happy/failure - `uv run pytest tests/integration/test_strict_full_diff_parity.py -q`; run twice with randomized scheduling hooks if already available, never sleeps. Record canonical hashes and receipts in `<attemptDir>/task-13-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `test(diff): prove serial parallel byte equivalence`

- [ ] 14. Prove registered FastMCP failures are nonpartial and never cached
  - What to do: strengthen `tests/integration/test_full_diff_mcp_surface.py` with actual `GetPRDiffUseCase`, fake strict session readers, recording cache, canonical coalescer, real `ToolRegistry` registration, FastMCP client calls, and recording metrics. Parameterize every `FullDiffIncompleteReason`, including `SNAPSHOT_CHANGED`, plus GitHub/GitLab operational pagination, auth, rate-limit, timeout, malformed snapshot, internal `TypeError`, and compare failure.
  - What to do: for each E5020 case parse raw tool JSON and assert exact code/reason, absent `files`, zero cache sets, one failure metric, and session closure. Operational cases assert their existing mapped codes and the same no-partial/no-write/metric guarantees. Positive control: authoritative zero files returns a successful empty list and exactly one cache write.
  - Must NOT do: no bypass of use-case/cache handling through a direct PRDiff-returning stub, no prose message pin beyond machine-consumed code/reason keys, and no real network/client construction.
  - Parallelization: Wave 3 | Blocked by: 2, 7, 8, 9, 10, 11, 12 | Blocks: 15, 17, 18 | Can parallelize with: 13 | Exclusive owner: `tests/integration/test_full_diff_mcp_surface.py` and only necessary focused `test_tool_registry.py` additions.
  - Recommended task executor category: `deep` - this is the public all-or-nothing proof across registration, coalescing, use case, cache, metrics, and serialization.
  - References: `prdiffer/application/tool_registry.py:267-369`; `prdiffer/application/pr_diff_executor.py:31-84`; `prdiffer/domain/usecases/pr_diff_usecases.py:50-114`; `prdiffer/domain/exceptions.py:273-375`; `tests/integration/test_full_diff_mcp_surface.py`; `tests/unit/application/test_tool_registry.py`.
  - Acceptance criteria: each E5020 returns `isError=true` with exactly machine-readable `error_code`, safe `details.reason`, and no `files`; operational codes are not remapped; cache.set is zero on all failures and one on successful empty/full results; failure metric increments once per failed call; same-key cancellation leaves no pending state.
  - QA scenarios: happy - `uv run pytest tests/integration/test_full_diff_mcp_surface.py -k 'success or authoritative_empty' -q`; failure - `uv run pytest tests/integration/test_full_diff_mcp_surface.py tests/unit/application/test_tool_registry.py -k 'E5020 or operational or cache or metric or cancellation' -q`. Save decoded raw payloads in `<attemptDir>/task-14-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `test(mcp): prove strict failures are nonpartial and uncached`

- [ ] 15. Lock strict cache namespace, validation, and no-write behavior across providers
  - What to do: add `tests/integration/test_strict_cache_contract.py` using real cache wrap/unwrap and use-case logic. Cover GitHub v3 exact identity, v2 bare/wrapped rejection, same-head/different-merge-base rebuild, base-tip-only stability, optimistic-token mismatch, GitLab v1 host/version/base/start/head stability, cache hit with session close, and zero writes for inventory/content/generation/deadline/cancellation/snapshot failures.
  - Must NOT do: no production cache migration, TTL/store redesign, GitLab key change, or reliance on unit-only mocked cache calls without observable reconstruction suppression.
  - Parallelization: Wave 3 | Blocked by: 1, 6, 11, 12, 14 | Blocks: 18 | Can parallelize with: 13 | Exclusive owner: new strict-cache integration module. This is proof-only; any failure reopens the numbered production todo that owns the violated seam.
  - Recommended task executor category: `unspecified-high` - provider-neutral cache integration with a bounded identity/failure matrix.
  - References: `prdiffer/domain/entities/pr_diff_cache.py`; `prdiffer/domain/usecases/pr_diff_usecases.py:92-114`; `prdiffer/infrastructure/github/pr_diff_session.py:61-70`; `prdiffer/infrastructure/vcs_providers/gitlab_diff_session.py:63-82`; `tests/unit/domain/test_pr_diff_cache_v2.py`; `tests/unit/domain/test_gitlab_pr_diff_cache.py`; `tests/unit/domain/usecases/test_session_pr_diff_usecase.py`.
  - Acceptance criteria: no old or mismatched entry can hit; exact identities hit without build; each successful miss writes exactly one complete entry under the current provider key/token; every listed failure writes zero; sessions close on hit, miss, and failure; GitLab behavior remains byte-identical.
  - QA scenarios: happy/failure - `uv run pytest tests/integration/test_strict_cache_contract.py tests/unit/domain/test_pr_diff_cache_v2.py tests/unit/domain/test_gitlab_pr_diff_cache.py -q`. Record cache keys/tokens and call counts in `<attemptDir>/task-15-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `test(cache): lock strict provider identities and failure writes`

- [ ] 16. Adversarially prove GitHub cannot return a mixed metadata/content snapshot
  - What to do: add `tests/integration/test_github_snapshot_atomicity.py` with a stateful provider that serves snapshot A at open, mutates to B before or during unversioned file enumeration, and records refs/object bytes/cache writes. Cover A->B head, merge-base, and changed-count mutations independently and together; include stable A and base-tip-only-change controls. The result must be one coherent A snapshot or E5020 `SNAPSHOT_CHANGED`, never mixed A/B.
  - Must NOT do: no retry to B, no test that asserts only getter counts, no provider-state mutation hidden inside expected-value construction, and no sleep-based race.
  - Parallelization: Wave 4 | Blocked by: 1, 6, 8, 11 | Blocks: 18 | Can parallelize with: 17 | Exclusive owner: new GitHub snapshot-atomicity integration module.
  - Recommended task executor category: `deep` - stateful adversarial mutation must prove observable bytes and cache behavior, not implementation calls.
  - References: `prdiffer/infrastructure/github/pr_diff_session.py`; `prdiffer/infrastructure/services/pr_diff_service.py`; `prdiffer/infrastructure/github/inventory.py`; `prdiffer/domain/entities/pr_diff_cache.py`; audit finding at `/var/folders/fm/dhwbb9lj4yn1dkrn1qncq8sh0000gn/T/opencode/prdiffer-audit-20260807.Dpxgim/final-audit-report.md:104-109`.
  - Acceptance criteria: stable snapshot succeeds; changed head/merge-base/count fails exact E5020 and zero cache sets; base-tip change with same merge-base/head/count remains coherent; no output contains base bytes from one snapshot and head/inventory bytes from another; session closes once.
  - QA scenarios: happy/failure - `uv run pytest tests/integration/test_github_snapshot_atomicity.py -q`. Use provider events/state transitions, not wall time; record state trace and receipt in `<attemptDir>/task-16-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `test(github): prove strict snapshot atomicity`

- [ ] 17. Adversarially prove cancellation, deadline, and capacity behavior across requests
  - What to do: add `tests/integration/test_strict_diff_concurrency.py` using the canonical coalescer, real session/use-case path, capacity-one provider workers, AnyIO events, and recording cache. Cover owner cancellation with an attached waiter, a non-abandoned late GitHub worker with a queued second request, GitLab sibling cancellation plus real root failure, and same-key retry after cleanup.
  - Must NOT do: no sleeps, raw asyncio, abandoned threads, polling loops, or assertions that pass before blocked workers and waiters actually terminate.
  - Parallelization: Wave 4 | Blocked by: 2, 7, 9, 13, 14 | Blocks: 18 | Can parallelize with: 16 | Exclusive owner: new strict concurrency integration module.
  - Recommended task executor category: `deep` - cross-request AnyIO scheduling, limiter ownership, coalescer state, and error identity require coordinated adversarial QA.
  - References: `prdiffer/infrastructure/utils/coalescing_service.py`; `prdiffer/infrastructure/utils/parallel/executor.py`; `prdiffer/infrastructure/github/pr_diff_session.py`; `prdiffer/infrastructure/vcs_providers/gitlab_runtime.py`; `prdiffer/infrastructure/vcs_providers/gitlab_content.py`; `prdiffer/application/pr_diff_executor.py`.
  - Acceptance criteria: cancelled owner and waiter terminate; pending/waiter counts return to zero; later same-key request succeeds; second capacity-one worker cannot enter before first non-abandoned worker exits; late result is discarded as E5004 with no cache write; GitLab non-cancellation root wins; no background task/thread remains at test teardown.
  - QA scenarios: happy/failure - `uv run pytest tests/integration/test_strict_diff_concurrency.py tests/performance/test_gitlab_strict_full_diff.py -k 'capacity or deadline or cancel or coalesc or root' -q`. Persist event order and stats in `<attemptDir>/task-17-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `test(concurrency): prove strict request cleanup and capacity`

- [ ] 18. Update strict-diff documentation and agent guidance
  - What to do: after behavior and taxonomy are final, update `README.md`, `skills/prdiffer/SKILL.md`, and only the current knowledge-base `AGENTS.md` files whose v2 identity/reason/object/session claims became stale. Document GitHub three-dot merge-base semantics, v3 key and unchanged value schema, old-key rejection, exact symlink/gitlink rendering, `SNAPSHOT_CHANGED`, operational-versus-E5020 boundaries, serial/parallel equivalence, and no-network verification. Keep historical completed plan files unchanged.
  - Must NOT do: no release/version bump, settings change, changelog invention, historical `docs/plans/*.md` rewrite, promotional prose, or documentation test that pins natural-language sentences.
  - Parallelization: Wave 4 | Blocked by: 4, 5, 11, 12, 13, 14, 15, 16, 17 | Blocks: F1-F4 | Exclusive owner: documentation and skill files after all behavior has stabilized.
  - Recommended task executor category: `writing` - exact technical contract synchronization without code changes.
  - References: `README.md:150-215`; `skills/prdiffer/SKILL.md:90-115,230-315`; stale current references found in root `AGENTS.md`, `prdiffer/domain/AGENTS.md`, `prdiffer/domain/entities/AGENTS.md`, `prdiffer/domain/interfaces/AGENTS.md`, `prdiffer/infrastructure/github/AGENTS.md`, `tests/unit/domain/entities/AGENTS.md`, and `tests/unit/infrastructure/github/AGENTS.md`; actual final source/tests from Todos 1-17 are authoritative.
  - Acceptance criteria: no current README/skill/AGENTS guidance claims GitHub v2 or base-tip semantics; all ten E5020 reasons are accurate; object and error behavior matches tests; GitLab v1 remains unchanged; historical plan files have zero diff; no prose assertions are added to tests.
  - QA scenarios: happy - the agent compares docs against final source/test symbols and records a structured checklist; failure guard - `rg -n 'github-full-diff-v2|GitHub v2' README.md skills/prdiffer/SKILL.md AGENTS.md prdiffer/**/AGENTS.md tests/**/AGENTS.md` returns only explicitly labeled historical/legacy rejection references. Run `uv run ruff check .` to ensure no accidental code edits. Evidence: `<attemptDir>/task-18-strict-full-diff-correctness-remediation.txt`.
  - Commit: Y | `docs(diff): document immutable strict object semantics`

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Audit implementation against every plan contract
  - What to verify: independently map each Must have/Must NOT have and every Todo acceptance criterion to the final diff and evidence receipts. Confirm all 18 todos are complete, dependencies were respected, exclusive write sets did not produce lost edits, every behavior-changing todo has a regression-specific red receipt, every proof-only todo names and exercises its negative control, and no claim rests only on worker self-report.
  - Recommended task executor category: `unspecified-high` - independent goal/constraint verification.
  - Acceptance: return `APPROVE` only when every requirement has source/test/evidence proof; otherwise return `REJECT` with exact todo, path, and missing or contradictory evidence. Save `<attemptDir>/final-F1-strict-full-diff-correctness-remediation.md`.

- [ ] F2. Run code-quality, architecture, and security review
  - What to verify: load the `review-work` workflow and review the complete branch for correctness, type safety, clean-architecture direction, host/token isolation, cache poisoning, cancellation leaks, object-ID/path validation, binary/size boundaries, and missing tests. Run `uv run ruff check .`, `uv run ty check`, changed-file `ruff format --check`, and `python3 scripts/analyze_dependencies.py --path prdiffer`.
  - Recommended task executor category: `unspecified-high` - independent multi-angle post-implementation review.
  - Acceptance: all review lanes approve; Ruff and ty exit 0; changed files are formatted; dependency analysis has no new violation beyond the documented application-factory edge; no secret, raw content, provider URL credentials, or unsafe error detail crosses E5020. Save `<attemptDir>/final-F2-strict-full-diff-correctness-remediation.md`.

- [ ] F3. Execute no-network FastMCP and provider-fake QA
  - What to verify: run the registered FastMCP success/failure matrix, GitHub and GitLab strict integration matrices, snapshot atomicity, cache contract, serial/parallel parity, concurrency/capacity suite, and deterministic benchmark. Capture decoded MCP success/errors, cache call counts, event order, and canonical output hashes.
  - Recommended task executor category: `deep` - hands-on system QA through the actual public surface and concurrency boundaries.
  - Required commands: `uv run pytest tests/integration/test_github_strict_full_diff.py tests/integration/test_gitlab_strict_full_diff.py tests/integration/test_full_diff_mcp_surface.py tests/integration/test_strict_cache_contract.py tests/integration/test_strict_full_diff_parity.py tests/integration/test_github_snapshot_atomicity.py tests/integration/test_strict_diff_concurrency.py -vv --tb=short`; `uv run pytest tests/performance/test_full_diff_benchmark.py tests/performance/test_gitlab_strict_full_diff.py -v --tb=short`; `uv run pytest tests -v --tb=short`.
  - Acceptance: all commands exit 0; no network/client guard fires; success is ordered and complete; each failure has exact nonpartial code/reason, zero cache writes, cleanup, and correct metrics; serial/parallel hashes match. Save `<attemptDir>/final-F3-strict-full-diff-correctness-remediation.md`.

- [ ] F4. Verify scope fidelity and release readiness
  - What to verify: compare the final branch/worktree against its baseline and the approved plan. Confirm only strict-diff code/tests/docs changed; old cache entries are rejected without migration; GitLab v1 remains stable; no public DTO/tool signature, package version, dependency, settings, historical plan, unrelated formatting, or known architecture debt was changed.
  - Recommended task executor category: `unspecified-high` - adversarial scope and release-decision review.
  - Acceptance: return `APPROVE` only if the final repository state is clean except intended commits, every commit is atomic and paired with its tests, no unrelated user changes were overwritten, and the release verdict is supported by F1-F3. Save `<attemptDir>/final-F4-strict-full-diff-correctness-remediation.md`.

## Commit strategy
- Use one atomic commit per numbered todo, with the exact commit subject listed in that todo. Production behavior and its red-first regression tests stay in the same commit; proof-gap tasks may be test-only commits.
- Integrate commits in dependency order. Do not squash together merge-base/cache identity, inventory propagation, object acquisition, coalescing, or provider-boundary fixes; each has an independent rollback contract.
- Never split Todo 1's merge-base/snapshot/v3 identity/revalidation change, Todo 2's canonicalization/cancellation change, Todo 3's renderer/mode/EOF change, Todo 8's GitHub object/rename change, or Todo 9's GitLab object/root-failure change across commits.
- Run the listed focused gate before committing each todo and the wave gate before starting dependent work. Do not commit a red test without its fix, or a production fix without the test that proves the original regression.
- Use a task-owned worktree for branch/PR execution. Do not amend, force-push, bypass hooks, hand-edit lockfiles, or stage unrelated files. The plan artifact itself does not authorize implementation or commits; `$start-work` execution does.
- Roll back only whole atomic commits. Never revert only the cache-key half of Todo 1 or delete/weaken a regression test to restore green.

## Success criteria
- GitHub builds every strict diff from one validated merge-base/head/count snapshot, uses the same merge-base for base-side trees/content and v3 cache identity, and fails `SNAPSHOT_CHANGED` rather than returning mixed state.
- A provider/pagination/compare/content/generation/deadline/cancellation failure can never become a successful empty or partial `PRDiff`, and never invokes strict cache `set`.
- Authoritative zero-file GitHub/GitLab snapshots still return and cache one valid empty result.
- Symlink and gitlink changes for both providers use immutable object identities and canonical Git-style text/mode/EOF semantics without target/submodule traversal; regular binary/NUL/invalid UTF-8/oversize cases fail with exact E5020 reasons.
- Custom GitLab hosts are forwarded exactly once and can never fall back to GitLab.com after an internal exception.
- Coalesced owner cancellation wakes waiters, removes pending state, propagates cancellation, and permits same-key recovery; indexed GitLab failures preserve the first stable non-cancellation root.
- GitHub rejects post-deadline worker results while holding capacity until worker exit; deterministic capacity tests leave no task/thread/session leaks.
- GitLab `++`/`--` stats and `real_size` parsing are exact; malformed GitHub renames fail E5020 before content acquisition.
- Serial and parallel outputs are byte-identical for every supported status/object mode and expose identical failure class/code/reason/details.
- Registered MCP E5020 has machine-readable code/reason, no `files`, one failure metric, and zero cache writes; operational provider errors retain their existing codes.
- Full pytest, focused/performance suites, Ruff, ty, changed-file formatting, and dependency analysis meet the verification contract without live network or credentials.
- README, shipped skill, and current knowledge-base guidance match the final v3/object/snapshot behavior; historical plans and unrelated hygiene remain untouched.
- F1, F2, F3, and F4 all return unconditional `APPROVE`, and the user explicitly accepts their surfaced results before execution is declared complete.
