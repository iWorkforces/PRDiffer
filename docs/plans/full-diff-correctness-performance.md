# full-diff-correctness-performance - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** Pull-request diffs that either contain complete, correctly ordered full-file context for every selected file or fail with a precise machine-readable reason. The work also makes GitHub access event-loop safe, adds guarded parallelism, and produces trustworthy before/after performance evidence.

**Why this approach:** Correctness and completeness are locked before optimization, so faster execution cannot amplify wrong-file mapping, silent omissions, or partial caching. Synchronous GitHub access is isolated and proven safe before any concurrency is enabled.

**What it will NOT do:** It will not replace core dependencies, redesign GitLab, remove intentional file-selection rules, return partial/truncated fallbacks, or promise unmeasured speedups.

**Effort:** XL
**Risk:** High - strict completeness intentionally rejects PRs that exceed configured limits or contain selected files whose full text cannot be reconstructed.
**Decisions to sanity-check:** Strict all-or-nothing responses; the file limit becomes a hard admission limit; configured filtering remains the explicit selection boundary; parallel GitHub fetching stays disabled by default until its safety gates pass.

Your next move: wait for the required dual high-accuracy review, then execute separately with `$start-work full-diff-correctness-performance`. Full execution detail follows below.

---

> TL;DR (machine): XL/high-risk strict full-diff correctness, typed failures, ordered identity-safe processing, anyio-isolated PyGithub, opt-in bounded concurrency, cache migration, real MCP QA, and baseline-driven performance validation.

## Scope
### Must have
- A successful GitHub `PRDiff` is complete by construction for every file selected by the existing ignore/extension policy; no selected file may be patch-only, silently skipped, truncated, or mapped to another file's content.
- Strict rejection through `E5020_FULL_DIFF_INCOMPLETE` for selected-file count overflow, provider inventory truncation/mismatch, binary or oversized selected content, deterministic unavailable/undecodable content, unsupported status, known inability to generate a complete diff, and response-size overflow. Unexpected algorithm/runtime defects retain `E5003_DIFF_GENERATION_ERROR`; retry-exhausted provider/network failures retain their existing operational error.
- Stable provider order; correct added, modified, deleted, renamed-with-change, rename-only, and legitimate empty-file behavior; public `previous_path` for renames.
- Public `FileDiffResponse.diff` remains the full-context string field. A provider patch is an internal generation input, not the returned artifact. No `complete` flag is added because every successful response is complete by invariant.
- Typed content acquisition that distinguishes valid empty text from unavailable content and keys caches by repository, path, and immutable ref.
- Authoritative PR changed-file count validation, complete pagination validation through 3,000 files, then existing configured filtering, then the strict selected-file admission limit.
- Synchronous PyGithub and retry work isolated behind anyio worker threads, initially serialized through a dedicated GitHub `CapacityLimiter`; no nested event-loop entry.
- Optional bounded concurrency only after identity, ordering, error, client ownership, rate-limit, timeout, cancellation, and cleanup contracts pass.
- A repaired deterministic benchmark with machine-readable baseline/post-change artifacts and correctness/API/concurrency/memory checks before performance claims.
- Unit, service integration, in-memory FastMCP, cancellation/coalescing, configuration, cache migration, documentation, lint, type, architecture, and full-suite verification.
### Must NOT have (guardrails, anti-slop, scope boundaries)
- Do not replace PyGithub, FastMCP, Dynaconf, anyio, the cache service, or the provider registry.
- Do not redesign GitLab. Adapt only the additive `previous_path` field mechanically with `None` when unavailable.
- Do not remove the documented ignore/extension selection policy. Strict completeness applies after selection, while provider inventory must be proven complete before selection.
- Do not return partial files, provider-patch fallbacks, truncation notices, `EDIT_TYPE.UNKNOWN`, or empty-success `PRDiff` values for completeness failures.
- Do not cache unavailable file content, old-format/partial PRDiff values, exceptions, cancelled work, or incomplete results.
- Do not call `anyio.run()` below an async entry point, use bare `asyncio`, share one mutable PyGithub client concurrently, abandon worker threads on cancellation, or add a second retry loop around PyGithub.
- Do not enable parallel settings until sequential event-loop safety and indexed all-or-error results are proven.
- Do not introduce unrelated retry, authentication, rate-limiter, circuit-breaker, logging, architecture, lint, or large-file refactors.
- Do not claim a fixed speedup or hard latency target before the repaired baseline establishes measurement noise.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: mandatory RED -> GREEN TDD with pytest and `@pytest.mark.anyio`; no real GitHub calls. Each production todo first runs its named test and captures the defect-specific assertion failure, then applies the minimum implementation and reruns the same test green.
- Test layers: pure domain/unit tests; mocked PyGithub adapter tests; service/inventory/processor integration tests; in-process FastMCP `Client` tests against the real registered tool; deterministic synthetic benchmarks.
- Hard correctness gates: exact provider order and path/content identity; complete selected inventory; full surrounding file context differs from a hunk-only provider patch; strict error code/reason; no returned files and zero PRDiff cache writes on failure.
- Async gates: event-loop heartbeat advances during blocking fake PyGithub work; no `anyio.run`; dedicated limiter bound holds; reverse completion order does not affect output; cancellation leaves no coalescing entry or cache write.
- Benchmark gates: fixture manifest/digest, page/API counts, selected mode marker, maximum in-flight work, heartbeat, wall/CPU time, `tracemalloc` peak, RSS delta, and per-sample output. Timing is reported, not used as a hard pass threshold until baseline noise is known.
- Project gates: `./start-type-check.sh --check`, `./start-lint.sh --check`, `python scripts/analyze_dependencies.py --path prdiffer`, focused pytest selections, then `./start-unittest.sh --run`.
- Evidence: `<attemptDir>/task-<N>-full-diff-correctness-performance.{red,green,surface,bench}.txt|json` where `attemptDir` is the current ulw attempt directory; outside ulw-loop use `.omo/evidence/full-diff-correctness-performance/`.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.

- Wave 0 - mandatory baseline gate: Todo 1 completes and its immutable `strict-v1` baseline artifact is captured before any production or contract todo begins.
- Wave 1 - independent foundations after baseline: Todos 2-5. Define strict errors, add rename metadata, normalize configuration, and add an indexed executor contract. These targets are disjoint enough to run concurrently only after Todo 1 passes.
- Wave 2 - strict building blocks: Todos 6-10. Implement typed content, authoritative inventory, rejection limits, deterministic full-context generation, and serialized worker isolation. Run only dependency-compatible items in parallel.
- Wave 3 - active-flow integration: Todos 11-14. Assemble ordered file processing, service/error/cache semantics, and finally opt-in bounded concurrency. Follow dependency order; do not enable concurrency early.
- Wave 4 - public surface and evidence: Todos 15-16. Verify the real MCP contract and docs, then capture post-change performance and run full gates.
- After every todo: run its focused tests, LSP diagnostics on every changed Python file, the task's real-surface command, and create its atomic commit before starting a dependent todo.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | none | 2, 3, 4, 5, 16 | none |
| 2 | 1 | 6, 7, 8, 9, 10, 12 | 3, 4, 5 |
| 3 | 1 | 9, 11, 12, 15 | 2, 4, 5 |
| 4 | 1 | 6, 7, 8, 10, 14 | 2, 3, 5 |
| 5 | 1 | 9, 14 | 2, 3, 4 |
| 6 | 2, 4 | 11, 13, 14 | 7, 8, 9, 10 |
| 7 | 2, 4 | 11, 12 | 6, 8, 9, 10 |
| 8 | 2, 4 | 12 | 6, 7, 9, 10 |
| 9 | 2, 3, 5 | 11, 12, 14 | 6, 7, 8, 10 |
| 10 | 2, 4 | 11, 14 | 6, 7, 8, 9 |
| 11 | 3, 6, 7, 9, 10 | 12, 14 | none |
| 12 | 2, 3, 7, 8, 9, 11 | 13, 15 | none |
| 13 | 6, 12 | 15 | 14 |
| 14 | 4, 5, 6, 9, 10, 11 | 15, 16 | 13 |
| 15 | 3, 12, 13, 14 | 16 | none |
| 16 | 1-15 | final verification | none |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [ ] 1. Repair the deterministic benchmark and capture the pre-change baseline
  - What to do: Refactor `scripts/bench_diff_generation.py` to use a frozen fake repository with `full_name`, deterministic fake PR files/content/pages, explicit `sync-current` and `async-current-negative-control` modes, warmups/repetitions, and JSON output. Define the immutable benchmark matrix `strict-v1`: `medium` = 25 files x 200 lines x 5 measured samples; `large` = 250 files x 1,000 lines x 5 samples; `pathological` = 10 files x 5,000 repeated/near-matching lines x 3 samples. All workloads use seed `5020`, one warmup excluded from samples, and identical fixture manifests across phases. Record wall/CPU time, Python allocation peak, normalized RSS, API/page/byte counts, ordered output manifest/digest, heartbeat, and max in-flight work. Mark future post-change modes as `unsupported` during the baseline; never time two labels that call the same path. Add `tests/performance/test_full_diff_benchmark.py` for fixture validity and mode-selection markers. Capture and seal the baseline before Todo 2 starts.
  - Must NOT do: No production behavior changes, live GitHub/network calls, random fixtures, cache leakage between samples, or fixed speed threshold.
  - Parallelization: Wave 0, run alone | Blocked by: none | Blocks: 2, 3, 4, 5, 16
  - References: `scripts/bench_diff_generation.py:1-153`; `prdiffer/infrastructure/github/file_processor.py:101-176`; `prdiffer/infrastructure/github/diff_generator.py:44-56`; `tests/performance/test_performance.py`; `settings.toml:41-48,167-191`.
  - Acceptance criteria: `uv run pytest tests/performance/test_full_diff_benchmark.py -q` passes; `uv run python scripts/bench_diff_generation.py --matrix strict-v1 --phase baseline --modes sync-current,async-current-negative-control --json <attemptDir>/task-1-full-diff-correctness-performance.baseline.json` exits 0 with the exact workload/sample matrix, ordered manifests/digests, zero network calls, and mode-specific validity markers; the negative control records event-loop blocking rather than claiming safety. Record the baseline file SHA-256 in task evidence and refuse overwrite.
  - QA scenarios: Happy: run the exact baseline command and validate all three workloads/schema/counters. Failure: rerun against the same output path and assert overwrite refusal; run an intentionally invalid repository fixture and assert preflight failure before timing. Evidence: `<attemptDir>/task-1-full-diff-correctness-performance.{red,green,surface}.txt` and `.baseline.json`.
  - Recommended task executor category: `unspecified-high` - the harness spans script, performance tests, async instrumentation, and evidence design.
  - Commit: Yes | `Repair full diff benchmark harness`

- [ ] 2. Define the strict completeness error and stable reason taxonomy
  - What to do: Add `E5020_FULL_DIFF_INCOMPLETE` in `prdiffer/domain/error_codes.py`, re-export it through `prdiffer/domain/errors.py`, add `FullDiffIncompleteReason` as a `StrEnum`, and add `FullDiffIncompleteError(GitHubAPIError)` in `prdiffer/domain/exceptions.py`. Reasons are exactly `INVENTORY_TRUNCATED`, `FILE_COUNT_LIMIT`, `BINARY_CONTENT`, `FILE_SIZE_LIMIT`, `CONTENT_UNAVAILABLE`, `CONTENT_DECODE_FAILED`, `UNSUPPORTED_FILE_STATUS`, `DIFF_GENERATION_FAILED`, and `RESPONSE_SIZE_LIMIT`. Safe details may contain `reason`, `path`, `previous_path`, `observed`, and `limit`, never token/raw content.
  - Must NOT do: Do not remap authentication, permission, rate-limit, or retry-exhausted network failures to E5020. Contract-recognized diff failure (missing output, identity/count mismatch, builder-declared inability) is E5020/DIFF_GENERATION_FAILED; an unexpected algorithm/runtime exception is E5003.
  - Parallelization: Wave 1 | Blocked by: 1 | Blocks: 6, 7, 8, 9, 10, 12
  - References: `prdiffer/domain/error_codes.py:224-378`; `prdiffer/domain/errors.py`; `prdiffer/domain/exceptions.py:269-329`; `prdiffer/application/tool_registry.py:304-323`; `docs/error-codes.md` if tracked.
  - Acceptance criteria: New tests in `tests/unit/domain/test_full_diff_incomplete_error.py` assert the exact code, every enum value, safe structured details, and `str(error)`; all existing error-code uniqueness tests pass.
  - QA scenarios: Happy: construct each reason and serialize safe details. Failure: attempt details containing raw content/token and assert the typed constructor rejects or excludes them. Evidence: `<attemptDir>/task-2-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `unspecified-high` - this is a cross-file public error contract with security-sensitive serialization.
  - Commit: Yes | `Add strict full diff completeness error`

- [ ] 3. Add previous-path metadata without weakening the success invariant
  - What to do: Add `previous_path: str | None = None` to frozen `FileDiffResponse`, preserve `diff: str`, and update entity/PRDiff serialization tests. Map GitLab mechanically to `None` or its existing old-path value; do not alter GitLab retrieval. Do not add a completeness boolean because success is complete by construction.
  - Must NOT do: Do not rename/remove `diff`, add compatibility aliases, or redesign provider interfaces.
  - Parallelization: Wave 1 | Blocked by: 1 | Blocks: 9, 11, 12, 15
  - References: `prdiffer/domain/entities/file_diff_response.py:12-43`; `prdiffer/domain/entities/file_patch.py:16-43`; `prdiffer/domain/entities/pr_diff.py:6-17`; `prdiffer/infrastructure/vcs_providers/gitlab_repository.py`; `tests/unit/domain/entities/test_file_diff_response.py`; `tests/unit/infrastructure/test_gitlab_vcs_provider.py`.
  - Acceptance criteria: `uv run pytest tests/unit/domain/entities/test_file_diff_response.py tests/unit/domain/entities/test_pr_diff.py tests/unit/infrastructure/test_gitlab_vcs_provider.py -q` passes and `asdict(FileDiffResponse(...))` contains `previous_path` with the expected string or null.
  - QA scenarios: Happy: renamed response serializes old/new paths. Failure: non-renamed entries with an accidental previous path are rejected by a domain invariant or mapping test. Evidence: `<attemptDir>/task-3-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `quick` - additive domain field plus direct mapper/entity tests.
  - Commit: Yes | `Expose previous path in file diff responses`

- [ ] 4. Make GitHubConfig the authoritative active-flow configuration
  - What to do: Extend frozen `GitHubConfig` and its typed interface with `max_file_size_bytes`, `max_total_chars`, `parallel_file_fetch_enabled`, `parallel_head_base_fetch_enabled`, `parallel_diff_generation_enabled`, and `pr_diff_request_timeout_seconds`. Load all values from the `default` Dynaconf environment with environment overrides, validate every size/count/timeout as positive, and require `github.timeout < mcp.pr_diff_request_timeout_seconds`. Preserve `github.timeout = 30` seconds and add `mcp.pr_diff_request_timeout_seconds = 180` as the exact default. Have `InfrastructureFactory.create_pr_diff_service()` pass one config-derived set of exact sentinel values to client, processor, generator, service, and `PRDiffExecutor`/coalescing owner deadline. Change performance flags to resolve correctly and remain false by default until Todo 14; serialized GitHub worker capacity is one when parallel fetch is disabled.
  - Must NOT do: Do not keep duplicate fallback paths with different defaults, silently coerce invalid nonpositive values, or enable concurrency in this todo.
  - Parallelization: Wave 1 | Blocked by: 1 | Blocks: 6, 7, 8, 10, 14
  - References: `prdiffer/infrastructure/settings.py:74-163`; `prdiffer/domain/config/github_config.py:15-140`; `prdiffer/domain/config/github_config_interface.py:12-94`; `prdiffer/infrastructure/factories/infrastructure_factory.py:112-168`; `prdiffer/infrastructure/github/client.py:65-104`; `settings.toml:1-48,167-191`; `tests/unit/infrastructure/test_concurrency_settings.py`.
  - Acceptance criteria: Factory tests inject distinct non-default values for every field and assert the active service graph receives each exact value; real `settings.toml` resolves all performance keys and exact 30/180 timeout defaults; environment override tests use values different from defaults; invalid zero/negative limits or `github.timeout >= request timeout` raise `ConfigurationError`.
  - QA scenarios: Happy: instantiate the active factory with sentinel settings and inspect consumers, including coalescing deadline. Failure: set `app.max_files_allowed=0` and then `github.timeout=180` with request timeout 180; each fails before a GitHub client is initialized. Evidence: `<attemptDir>/task-4-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `unspecified-high` - shared typed configuration and DI wiring span domain and infrastructure.
  - Commit: Yes | `Wire full diff settings through GitHubConfig`

- [ ] 5. Add an indexed all-or-error async batch contract
  - What to do: Add an immutable indexed/keyed batch result API to `AsyncParallelExecutor` that stores outcomes by submitted index, preserves failures with their item identity, and returns in input order. Keep legacy methods for unrelated callers, but migrate full-diff callers later. Define strict mode so one failure cancels siblings and propagates; no completion-order append, result compaction, or positional zip.
  - Must NOT do: Do not change unrelated executor callers, use `asyncio`, suppress worker exceptions, or expose `Any` in the new public signatures.
  - Parallelization: Wave 1 | Blocked by: 1 | Blocks: 9, 14
  - References: `prdiffer/infrastructure/utils/parallel/executor.py:91-145,334-380`; `prdiffer/infrastructure/github/client_operations.py:261-289`; `prdiffer/infrastructure/github/diff_generator.py:280-302`; `tests/unit/infrastructure/test_async_parallel_executor.py`.
  - Acceptance criteria: `uv run pytest tests/unit/infrastructure/test_async_parallel_executor.py -q` includes controlled reverse-completion, failed-middle-item, duplicate-key, timeout, and cancellation cases; output identity/order matches submission and strict failure never returns a compacted list.
  - QA scenarios: Happy: complete `c,a,b` and assert returned indices `a,b,c`. Failure: fail `b` and assert the batch raises with `b` identity and no partial values escape. Evidence: `<attemptDir>/task-5-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `deep` - concurrency semantics affect multiple latent corruption paths.
  - Commit: Yes | `Add indexed async batch execution`

- [ ] 6. Introduce typed file-content results and repository-scoped caching
  - What to do: Add a pure-domain discriminated union `FileContentAvailable(text: str)` and `FileContentUnavailable(reason, path, ref, observed_size)`; unavailable is limited to deterministic content facts: binary, size limit, directory/non-file response, not-found where the selected status requires that side, and decode failure. Change GitHub content interfaces, sync/async client operations, and batches to return typed results. A valid zero-byte file is available with `text == ""`. Authentication, permission, rate-limit, transport, timeout, and retry-exhausted failures raise their existing operational exception and never become a union value. Cache only available values and change the cache key to `(repo_full_name, path, immutable_ref)`.
  - Must NOT do: Do not cache unavailable results, return empty-string sentinels, use `cast`/`Any`, or convert any operational GitHub/rate-limit/retry-exhausted exception into E5020.
  - Parallelization: Wave 2 | Blocked by: 2, 4 | Blocks: 11, 13, 14
  - References: `prdiffer/domain/services/github_api.py:39-76`; `prdiffer/infrastructure/github/client_operations.py:121-198,200-325`; `prdiffer/infrastructure/github/client.py:65-104`; `tests/unit/infrastructure/github/test_api_client_comprehensive.py`.
  - Acceptance criteria: Focused tests distinguish valid empty, binary, exact-size, size-plus-one, directory, decode failure, required-side not-found, transient/retry-exhausted operational exception, and same path/ref in two repositories; deterministic unavailable then successful fetch performs a second provider call; retry exhaustion propagates E5002/narrower provider error and performs zero cache writes.
  - QA scenarios: Happy: zero-byte content returns `FileContentAvailable("")` and is cacheable. Deterministic failure: binary/oversized content yields the exact unavailable reason and no cache entry. Operational failure: retry exhaustion raises the original typed provider error, not `FileContentUnavailable`. Evidence: `<attemptDir>/task-6-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `deep` - this changes the provider boundary, cache contract, and all content fetch variants.
  - Commit: Yes | `Model GitHub file content availability explicitly`

- [ ] 7. Validate authoritative inventory and strict selected-file admission
  - What to do: Fetch PR metadata once, capture immutable base/head SHAs and authoritative changed-file count, fully enumerate `get_files()` in source order, and require enumerated count equality. Reject authoritative counts over 3,000 before content calls; reject any mismatch below/equal 3,000. Apply existing ignore/extension policy only after inventory validation. Reject when selected count exceeds `max_files_allowed`; exactly N succeeds, N+1 fails before content loading. Preserve an authoritative zero-file PR as a valid empty inventory only when both counts are zero.
  - Must NOT do: Do not silently accept 3,000 when authoritative count is larger, stop pagination at the local limit, or remove configured filtering.
  - Parallelization: Wave 2 | Blocked by: 2, 4 | Blocks: 11, 12
  - References: `prdiffer/infrastructure/services/pr_diff_service.py:148-180,339-368`; `prdiffer/infrastructure/github_repository.py:331-341`; GitHub PR files endpoint `https://docs.github.com/en/rest/pulls/pulls?apiVersion=2026-03-10#list-pull-requests-files`; `tests/unit/infrastructure/test_pr_diff_service_comprehensive.py`.
  - Acceptance criteria: Fake pagination tests cover two pages in order, 2,999, exactly 3,000, authoritative 3,001, mismatch 250/249, selected N, selected N+1, and missing-patch N+1; failures assert E5020 reason, zero content calls, zero returned files, and zero PRDiff cache writes.
  - QA scenarios: Happy: authoritative/enumerated 3,000 with selected count within limit succeeds in provider order. Failure: authoritative 3,001 or mismatch fails before content loading. Evidence: `<attemptDir>/task-7-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `deep` - provider pagination, filtering, admission, and cache safety must agree.
  - Commit: Yes | `Reject incomplete GitHub file inventories`

- [ ] 8. Convert diff and response truncation into strict rejection policies
  - What to do: Replace successful truncation behavior with pure boundary checks. `max_diff_size` is the maximum character length of one generated public diff; `max_total_chars` is the sum of `len(response.diff)` over all files in provider order. Boundary minus one and exact boundary succeed; plus one raises `E5020/RESPONSE_SIZE_LIMIT`. Remove use of truncation notices from the strict path and enforce limits before `PRDiff` construction/cache.
  - Must NOT do: Do not slice strings, append `[DIFF TRUNCATED]`, partially assemble a response, or reinterpret limits as bytes.
  - Parallelization: Wave 2 | Blocked by: 2, 4 | Blocks: 12
  - References: `prdiffer/infrastructure/services/pr_diff_service.py:77-80`; `prdiffer/infrastructure/utils/diff_utils.py:76-120`; `settings.toml:173-182`; `tests/unit/infrastructure/test_diff_limits.py`; `tests/unit/infrastructure/test_pr_diff_service.py:34-68`.
  - Acceptance criteria: Pure and service tests prove per-file and aggregate minus-one/exact/plus-one behavior, no successful output contains the truncation notice, and failure returns/caches no files.
  - QA scenarios: Happy: aggregate exactly at the configured character count succeeds unchanged. Failure: one extra character raises E5020 with observed/limit and no cache write. Evidence: `<attemptDir>/task-8-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `unspecified-high` - semantics span diff utility, service assembly, configuration, and tests.
  - Commit: Yes | `Reject oversized full diff responses`

- [ ] 9. Make full-context generation deterministic, identity-bearing, and all-or-error
  - What to do: Introduce an immutable `GeneratedFileDiff(index, path, previous_path, diff)` result. Build a full-file unified representation from required base/head text, not the provider patch alone. Added uses known-empty base; deleted uses base and known-empty head; modified uses both; renamed uses `previous_path` for base and `path` for head. Rename-only output must contain deterministic `rename from`/`rename to` headers plus a full-context hunk when text exists; zero-byte add/delete/rename remains meaningful through headers/status. Missing provider patch is recoverable only from complete text. Sequential and indexed-parallel generation must return exactly one result per selected file or raise.
  - Must NOT do: Do not silently skip missing/unextendable patches, return completion order, conflate `+++`/`---` headers with additions/deletions, or use quadratic/chunked shortcuts without characterization tests.
  - Parallelization: Wave 2 | Blocked by: 2, 3, 5 | Blocks: 11, 12, 14
  - References: `prdiffer/infrastructure/utils/diff_utils.py:46-120,179-201`; `prdiffer/infrastructure/github/diff_generator.py:44-56,220-311`; `prdiffer/domain/services/diff.py`; `tests/unit/infrastructure/github/test_diff_generator_comprehensive.py`.
  - Acceptance criteria: Tests cover repeated lines, no-newline markers, large/chunk boundaries, provider hunk with surrounding unchanged lines, every edit status, missing provider patch, rename-only, builder-declared inability, identity/count mismatch, and unexpected algorithm exception; public candidate output contains all fixture lines and differs from the hunk-only patch.
  - QA scenarios: Happy: generate all statuses and assert one indexed full-context result per input in provider order. Contract failure: builder returns missing/identity-mismatched output and raises E5020/DIFF_GENERATION_FAILED with no partial result. Internal defect: builder raises an unexpected runtime/algorithm exception and the boundary returns E5003, never E5020. Evidence: `<attemptDir>/task-9-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `deep` - diff correctness, pathological complexity, and ordering share one cohesive algorithmic contract.
  - Commit: Yes | `Generate complete ordered file diffs`

- [ ] 10. Isolate synchronous PyGithub work behind a serialized anyio boundary
  - What to do: Create `prdiffer/domain/interfaces/pr_diff_reader.py` as a new capability module; leave the existing generic `PRDiffReader` behavior available to GitLab. Define frozen `PRDiffSnapshot(owner, repo, pr_number, base_sha, head_sha, authoritative_changed_files)`, `PRDiffReadSessionInterface` exposing immutable `snapshot`, async inventory/content operations and `aclose()`, and `@runtime_checkable SessionPRDiffReader(PRDiffReader, Protocol)` with `open_pr_diff_session(...)`. Update the use case to branch by this structural capability: session-capable GitHub readers use the new session/v2 path; non-session readers, including GitLab, execute the existing `get_latest_commit_sha()` -> cache -> `get_pr_diff()` path unchanged. Implement the GitHub session as infrastructure-owned with one request-local PyGithub client/repository/PR; domain/use-case never sees live SDK objects. Open once, fetch metadata once, reuse handles through cache lookup/build, and close in `finally`. Every sync operation runs through `anyio.to_thread.run_sync(..., abandon_on_cancel=False, limiter=github_limiter)`; initial capacity one. Use `github.timeout=30`, an absolute 180-second request deadline, and check remaining budget before retries/backoff. Pass the same deadline to the active coalescing owner.
  - Must NOT do: Do not use `anyio.run`, bare asyncio, `time.sleep` on the event loop, abandoned workers, duplicate retry loops, or concurrent access to one PyGithub client.
  - Parallelization: Wave 2 | Blocked by: 2, 4 | Blocks: 11, 14
  - References: `prdiffer/domain/usecases/pr_diff_usecases.py:7-16,35-71` (existing generic protocol and shared consumer); `prdiffer/domain/interfaces/pr_diff_reader.py` (new session-capability module to create); `prdiffer/application/pr_diff_executor.py:20-60` (shared GitHub/GitLab dispatch); `prdiffer/infrastructure/services/pr_diff_service.py:101-169`; `prdiffer/infrastructure/vcs_providers/gitlab_repository.py`; `prdiffer/infrastructure/github/client.py:74-221`; `prdiffer/infrastructure/github/client_operations.py:169-259`; `prdiffer/infrastructure/utils/retry/handler.py:32-132`; `prdiffer/infrastructure/utils/coalescing_service.py:46-174` (active canonical coalescer); AnyIO thread docs.
  - Acceptance criteria: Anyio tests prove capability dispatch selects the session path only for GitHub and preserves the existing GitLab reader call sequence/cache behavior; exactly one GitHub client/repository/PR metadata lookup per request session; closure on hit/miss/error/cancel; heartbeat progress; no `anyio.run`; max in-flight one; exact 30/180 deadlines; retry budget refusal; operational timeout propagation.
  - QA scenarios: GitHub happy: open one session, read snapshot, miss cache, build and close with one metadata lookup while heartbeat advances. GitHub cache hit: close without pagination/content calls. GitLab regression: a non-session fake executes the legacy two-method reader path and never receives/returns a session/v2 entry. Failure: cancel owner or exhaust deadline and assert original error plus zero writes/pending coalescing keys. Evidence: `<attemptDir>/task-10-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `deep` - event-loop safety, object ownership, retries, cancellation, and deadlines are tightly coupled.
  - Commit: Yes | `Isolate PyGithub calls from the event loop`

- [ ] 11. Rewrite FileProcessor as ordered strict status-aware assembly
  - What to do: Classify selected provider files once with their original indices and exhaustive status matching. Build required content keys as `(side, repo, path, ref, index)`, using `previous_filename` for renamed/deleted base paths. Load exactly the required sides through typed content and the serialized async adapter, reject any unavailable required content, then reconstruct `FilePatchInfo` in original order. Include deleted and rename-only files. Keep sync and async behavior equivalent or route both through one shared pure classification/assembly core.
  - Must NOT do: Do not maintain duplicated patch-dependent/off-by-one loops, append loaded/unloaded groups separately, skip removed/rename-only entries, or accept `EDIT_TYPE.UNKNOWN`.
  - Parallelization: Wave 3 | Blocked by: 3, 6, 7, 9, 10 | Blocks: 12, 14
  - References: `prdiffer/infrastructure/github/file_processor.py:101-176,178-330`; `tests/unit/infrastructure/github/test_file_processor_comprehensive.py:186-263`; `tests/conftest.py` fixtures.
  - Acceptance criteria: RED/GREEN tests assert sync/async parity and exact order for mixed added/modified/deleted/renamed/rename-only files; delayed completions retain identity; a failed middle file rejects the request; selected limit N succeeds and N+1 was already rejected before this stage.
  - QA scenarios: Happy: `[modified, deleted, renamed, rename-only, added]` returns the same ordered paths/statuses with correct old/new content. Failure: binary or unavailable middle content raises the exact reason and produces no list. Evidence: `<attemptDir>/task-11-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `deep` - this is the central correctness refactor across classification, content, and identity.
  - Commit: Yes | `Assemble selected PR files in provider order`

- [ ] 12. Return generated full-context diffs and propagate strict failures
  - What to do: Refactor `GitHubPRDiffService` around the Todo 10 request session: its build operation receives the already-open session/snapshot, consumes one identity-bearing generated diff per processed file, maps `GeneratedFileDiff.diff` into public `FileDiffResponse.diff`, maps `old_filename` to `previous_path`, enforces per-file/aggregate limits, and constructs `PRDiff` only after all validations pass. Replace `None`, `[]`, and `("", [])` operational fallbacks with typed exceptions. Preserve auth/rate/network/retry-exhausted codes; use E5020/DIFF_GENERATION_FAILED for builder-declared inability or identity/count mismatch and E5003 only for an unexpected internal algorithm/runtime exception. Record success metrics only after complete construction.
  - Must NOT do: Do not return `file_patch.patch`, catch-and-empty, create a partial tuple, or count a failed/empty generation as success.
  - Parallelization: Wave 3 | Blocked by: 2, 3, 7, 8, 9, 11 | Blocks: 13, 15
  - References: `prdiffer/infrastructure/services/pr_diff_service.py:82-196,207-257,325-368`; `prdiffer/application/pr_diff_executor.py:20-60`; `tests/unit/infrastructure/test_pr_diff_service_comprehensive.py`; `tests/unit/infrastructure/test_pr_diff_service_updates.py`.
  - Acceptance criteria: Service tests use a provider hunk plus larger base/head fixture and assert public `diff` includes surrounding lines; deleted/renamed metadata is preserved; every strict failure returns no PRDiff and records failure metrics; builder-declared inability is E5020 while unexpected exception is E5003; sync/native-async entry points use the same session-backed core.
  - QA scenarios: Happy: one mixed PR returns complete full-context strings through one session-backed core. Contract failure: missing generated identity reaches E5020/DIFF_GENERATION_FAILED, never `PRDiff(files=())`. Internal defect: unexpected algorithm exception reaches E5003. Evidence: `<attemptDir>/task-12-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `deep` - this integrates the public response invariant and all failure classifications.
  - Commit: Yes | `Return strict full-context PR diffs`

- [ ] 13. Version caches and preserve strict errors through coalescing
  - What to do: In the use case's `SessionPRDiffReader` branch only, open one GitHub session, read `snapshot.head_sha`, derive/cache/build through that session, and close in `finally`. The exact GitHub PRDiff key is `("github-full-diff-v2", owner.casefold(), repo.casefold(), pr_number, head_sha)` and value is frozen `PRDiffCacheEntryV2(schema_version=2, value=PRDiff)`. Accept only that type/version after complete-response validation; ignore/lazily replace unversioned, v1, raw, or wrong-schema values without bulk migration. The exact GitHub file-content key is `("github-file-content-v2", repo_full_name.casefold(), immutable_ref, normalized_posix_path)` and only `FileContentAvailable` is stored. The non-session branch preserves GitLab's existing cache key/value and reader flow; it never reads or writes GitHub-v2 entries. Remove/disable method-level PRDiff caching only on the GitHub session service path. Designate `prdiffer/infrastructure/utils/coalescing_service.py` as the canonical active implementation because application imports already target it; modify/test this flat module and correct test patch targets to it. Leave the inactive duplicate package `prdiffer/infrastructure/utils/coalescing/` untouched in this scope. Ensure active coalesced owner errors wake waiters identically; waiter timeout detaches; owner cancellation cleans state and writes no cache.
  - Must NOT do: Do not reuse old partial entries, negative-cache content failures, cache exceptions, or leave two conflicting PRDiff cache layers.
  - Parallelization: Wave 3 | Blocked by: 6, 12 | Blocks: 15 | Can parallelize with: 14
  - References: `prdiffer/domain/usecases/pr_diff_usecases.py:35-71`; `prdiffer/application/factory.py:67`; `prdiffer/application/mcp_server.py:84-86`; `prdiffer/application/tool_registry.py:82-84`; `prdiffer/infrastructure/services/pr_diff_service.py:207-257`; `prdiffer/infrastructure/cache/`; `prdiffer/infrastructure/utils/coalescing_service.py:1-220` (active canonical module); `prdiffer/infrastructure/utils/coalescing/service.py` (inactive duplicate, out of scope); `tests/unit/infrastructure/test_request_coalescing.py:10-14`; `tests/unit/infrastructure/utils/test_coalescing.py`.
  - Acceptance criteria: GitHub session tests seed exact unversioned/v1/raw/wrong-version values and ignore each; two calls share one owner session/provider result/error; success writes one exact v2 entry; strict/operational/cancel/timeout writes nothing and leaves zero pending keys. GitLab regression proves the non-session reader uses its existing key/value and never calls session/v2 APIs. Import/patch assertions prove application and both coalescing test files exercise the flat canonical module; the inactive package has no production import.
  - QA scenarios: GitHub happy: two coalesced calls share one session and exact-v2 entry. GitLab happy: two calls retain legacy reader/cache behavior without v2 values. Strict/operational failures are identical across waiters with no writes. Canonical-path regression: patch flat `coalescing_service.get_settings_service`, invoke application-resolved singleton, and assert the patch is observed. Evidence: `<attemptDir>/task-13-full-diff-correctness-performance.{red,green,surface}.txt`.
  - Recommended task executor category: `deep` - cache migration and async coalescing must preserve one atomic success/failure outcome.
  - Commit: Yes | `Version strict full diff caches`

- [ ] 14. Add opt-in bounded identity-preserving concurrency
  - What to do: Migrate full-diff content fetching and eligible CPU diff generation to the indexed executor. When parallel fetch is false, keep the serialized limiter of one. When true, create a bounded request-local client pool via an injected client factory; each client/session is owned by one worker at a time and explicitly closed. Use one shared GitHub limiter across the pool with `max_concurrent`; head/base and per-file work carry immutable side/path/ref/index keys. Strict failure cancels siblings and emits no partial result. Keep defaults false in `settings.toml` until all tests pass.
  - Must NOT do: Do not share a `Github`, `Requester`, `Repository`, `PullRequest`, or `PaginatedList` concurrently; target GitHub's 100-request ceiling; ignore `Retry-After`; or infer concurrency from elapsed time alone.
  - Parallelization: Wave 3 | Blocked by: 4, 5, 6, 9, 10, 11 | Blocks: 15, 16 | Can parallelize with: 13
  - References: `prdiffer/infrastructure/github/client_operations.py:261-289`; `prdiffer/infrastructure/utils/parallel/executor.py:91-145`; `prdiffer/infrastructure/github/diff_generator.py:280-311`; `settings.toml:41-48`; PyGithub Requester source and GitHub secondary rate-limit guidance cited in the draft.
  - Acceptance criteria: Tests prove `max_in_flight <= max_concurrent`, `max_in_flight > 1` for an eligible opt-in fixture, output identity/order equals sequential mode, all clients close, reverse completion is safe, one failure rejects all, retry headers are honored, and default configuration remains serialized.
  - QA scenarios: Happy: workers 1/2/4 produce identical ordered manifests and bounded counters. Failure: fail the middle worker and assert sibling cancellation, client closure, no response, and no cache write. Evidence: `<attemptDir>/task-14-full-diff-correctness-performance.{red,green,surface,bench}.txt|json`.
  - Recommended task executor category: `deep` - safe SDK ownership, structured concurrency, rate limits, and output identity are inseparable.
  - Commit: Yes | `Add bounded full diff concurrency`

- [ ] 15. Verify the real FastMCP contract and update public guidance
  - What to do: Add `tests/integration/test_full_diff_mcp_surface.py` using an in-process FastMCP `Client`, real `ToolRegistry` registration, deterministic fake authentication/rate limit/cache/GitHub reader, and a guard that fails on any real network/client construction. Cover successful modified/deleted/renamed output and strict binary/size/inventory/file-count/diff-size/aggregate/failure errors. Update `tool_registry.py` docstring, `README.md`, `skills/prdiffer/SKILL.md`, and tracked error documentation to describe all-or-nothing selected-file completeness, `previous_path`, E5020 reasons, hard admission/rejection limits, and actual MCP error payload parsing.
  - Must NOT do: Do not assert prose wording, require credentials/socket/manual clicks, document partial fallback, or change GitLab behavior beyond the shared field.
  - Parallelization: Wave 4 | Blocked by: 3, 12, 13, 14 | Blocks: 16
  - References: `prdiffer/application/tool_registry.py:235-325`; `tests/unit/application/test_tool_registry.py:79-89,441-474`; `tests/integration/test_complete_workflow.py`; `tests/integration/test_error_scenarios.py`; `README.md`; `skills/prdiffer/SKILL.md`.
  - Acceptance criteria: `uv run pytest tests/integration/test_full_diff_mcp_surface.py -q` calls the registered tool through FastMCP serialization; GitHub success uses the session/v2 route with ordered complete diffs and `previous_path`; GitLab success uses the legacy non-session route with only the additive shared field; failures expose E5020 and stable reason with no `files`; network guard remains untouched. Documentation review compares actual schema/error artifacts to docs without sentence-grep tests.
  - QA scenarios: GitHub happy: invoke `get_pr_diff` for a fake mixed PR and parse the serialized result. GitLab regression: invoke the same registered tool with a GitLab reader and prove no session/v2-cache method is touched. Failure: binary GitHub fake returns E5020/BINARY_CONTENT and zero success metrics/cache writes. Evidence: `<attemptDir>/task-15-full-diff-correctness-performance.{red,green,surface}.txt` plus serialized JSON.
  - Recommended task executor category: `unspecified-high` - integration code, transport schema, and public docs must agree.
  - Commit: Yes | `Document and verify strict MCP diff responses`

- [ ] 16. Capture post-change performance and run all quality gates
  - What to do: Run the exact Todo 1 `strict-v1` fixtures, seed, warmup, and samples with post-change modes `serialized-worker-1`, `bounded-worker-2`, and `bounded-worker-4`; write a separate post JSON and comparison output against the sealed baseline SHA-256. The script maps worker counts exactly to those mode names. Require identical workload manifests/digests across baseline and every post mode, no extra API/page calls, bounded in-flight work, no event-loop blocking, and no material memory regression hidden by faster wall time. Then run focused suites, full tests, type check, lint, and architecture analysis. Fix only regressions caused by this plan, rerunning affected evidence.
  - Must NOT do: Do not overwrite baseline evidence, claim a speedup outside measured workloads, relax correctness to improve timing, or fix unrelated pre-existing findings.
  - Parallelization: Wave 4 final implementation task | Blocked by: 1-15 | Blocks: final verification
  - References: Todo 1 artifact schema; `scripts/bench_diff_generation.py`; `tests/performance/`; root `AGENTS.md` quality commands.
  - Acceptance criteria: `uv run python scripts/bench_diff_generation.py --matrix strict-v1 --phase post --modes serialized-worker-1,bounded-worker-2,bounded-worker-4 --baseline <attemptDir>/task-1-full-diff-correctness-performance.baseline.json --json <attemptDir>/task-16-full-diff-correctness-performance.post.json` and `uv run python scripts/bench_diff_generation.py --compare <baseline> <post> --json <attemptDir>/task-16-full-diff-correctness-performance.comparison.json` exit 0. Baseline/post share schema; every digest matches; serialized heartbeat is healthy; bounded modes respect 2/4; comparative median/p95/CPU/memory/API deltas are reported. All project quality commands complete with no new failures.
  - QA scenarios: Happy: run the exact post and compare commands, then full gates. Failure: alter one copied manifest or baseline SHA and prove the comparator rejects before reporting performance. Evidence: `<attemptDir>/task-16-full-diff-correctness-performance.{surface,quality}.txt`, `.post.json`, and `.comparison.json`.
  - Recommended task executor category: `unspecified-high` - broad evidence collection and regression triage, with no new architecture.
  - Commit: No unless verification exposes a plan-caused defect; any fix is committed atomically with its regression test.

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit
  - Verify every todo's acceptance criteria and evidence receipt against the final diff; reject any partial/truncated success, missing RED proof, missing cache assertion, or enabled concurrency without ownership tests.
  - Invocation: read the plan and final diff, then run focused assertions from Todos 2, 7, 11-15. Evidence: `<attemptDir>/final-F1-plan-compliance.txt`.
  - Recommended task executor category: `unspecified-high`.
- [ ] F2. Code quality and architecture review
  - Review strict typing, exhaustive variants, domain purity, anyio correctness, PyGithub ownership, cache versioning, error security, file sizes, and absence of suppressed types/broad catch-and-empty paths.
  - Invocation: `./start-type-check.sh --check`, `./start-lint.sh --check`, `python scripts/analyze_dependencies.py --path prdiffer`, LSP diagnostics on every changed file. Evidence: `<attemptDir>/final-F2-code-quality.txt`.
  - Recommended task executor category: `deep`.
- [ ] F3. Real MCP and benchmark QA
  - Exercise the actual in-memory registered MCP tool for complete success and strict failures, then run the baseline/post comparator for medium, large, and pathological fixtures. Confirm teardown: no live tasks, clients, temporary caches, or network calls.
  - Invocation: `uv run pytest tests/integration/test_full_diff_mcp_surface.py tests/performance/test_full_diff_benchmark.py -q`; then the exact Todo 16 `--matrix strict-v1 --phase post --modes serialized-worker-1,bounded-worker-2,bounded-worker-4` command and exact `--compare <baseline> <post>` command. Evidence: `<attemptDir>/final-F3-real-surface.txt` and the sealed baseline/post/comparison JSON artifacts.
  - Recommended task executor category: `unspecified-high`.
- [ ] F4. Scope fidelity and regression review
  - Compare final changes to Must have/Must NOT have; verify intelligent filtering and GitLab behavior are preserved, no dependency replacement/unrelated cleanup landed, performance defaults remain safe, and every public behavior change is documented.
  - Invocation: inspect `git diff --stat`, `git diff`, and per-path history; run GitLab provider tests and the full suite. Evidence: `<attemptDir>/final-F4-scope-fidelity.txt`.
  - Recommended task executor category: `unspecified-high`.

## Commit strategy
- Repository history is mixed, but recent commits on the affected infrastructure paths use short plain-English subjects. Use one plain imperative commit per todo, pairing implementation and its direct tests; do not create RED-only commits.
- Dependency order: benchmark foundation -> domain/error/config/executor foundations -> content/inventory/limits/generation/worker boundary -> processor/service/cache/concurrency -> MCP/docs -> verification.
- Different directories may share a commit only when they are an inseparable implementation-test pair or one public contract plus its direct adapter tests. Any commit touching 3+ files must state that justification in the execution evidence.
- Expected subjects are the `Commit:` values on Todos 1-15. Todo 16 creates no commit unless it uncovers a plan-caused defect.
- Before every commit: inspect `GIT_MASTER=1 git status`, `GIT_MASTER=1 git diff`, `GIT_MASTER=1 git log --oneline -20`, and `GIT_MASTER=1 git log -5 -- <touched paths>`; stage only intended files and never commit `.env`, credentials, or unrelated worktree changes.

## Success criteria
- Every selected changed file appears exactly once in provider order with correct `path`, `previous_path`, status, stats, and generated full-context `diff`.
- Added, modified, deleted, renamed-with-change, rename-only, and legitimate empty files are complete; missing provider patches are recovered only from complete content.
- Inventory >3,000, inventory mismatch, selected count >limit, binary/oversized/unavailable/undecodable content, unsupported status, generation failure, per-file overflow, and aggregate overflow return the correct typed failure with no files and no PRDiff cache write.
- Valid empty content is distinct from unavailable content; content cache keys include repository/path/ref and never store failure sentinels.
- Retry-exhausted/auth/rate/network content failures preserve existing operational exceptions; only deterministic content limitations become E5020. Builder-declared inability/identity mismatch is E5020/DIFF_GENERATION_FAILED; unexpected internal algorithm/runtime exceptions are E5003.
- Public output uses generated full context rather than provider hunks; no truncation notice, partial tuple, catch-and-empty result, or stale v1 cache entry can escape.
- One request session performs one metadata lookup, provides the head SHA for cache selection, reuses request-local handles for a miss, and always closes. Exact v2 PRDiff/content keys reject all old/raw/wrong-schema entries.
- The session/v2 route is capability-selected for GitHub only; GitLab retains its current generic reader/cache path and receives only the additive `previous_path` schema adaptation.
- `prdiffer/infrastructure/utils/coalescing_service.py` is the tested canonical active coalescer; application imports and test patch targets agree, while the inactive package duplicate remains untouched.
- Event loop remains responsive during synchronous PyGithub work; exact 30-second provider and 180-second request/coalescing deadlines are wired and validated; no nested `anyio.run`; cancellation/coalescing cleanup is leak-free; default access is serialized.
- Opt-in concurrency preserves identity/order, owns/closes isolated clients, honors the shared bound and retry guidance, and is output-equivalent to serialized mode.
- Repaired baseline and post-change benchmarks are reproducible and validity-gated; all reported performance deltas include CPU, memory, API/page, concurrency, and correctness context.
- In-memory FastMCP success/error scenarios, all focused suites, full tests, type check, lint, LSP diagnostics, and architecture analysis pass with no new regressions.
- Final F1-F4 reviewers all approve, evidence and teardown receipts exist, the user explicitly accepts the final verification results, and no work beyond this scope was added.
