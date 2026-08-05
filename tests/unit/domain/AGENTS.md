# AGENTS.md - Domain Unit Tests

Pure domain tests without I/O (~5K+ lines across subpackages).

## STRUCTURE
```
tests/unit/domain/
├── entities/                         # Rich/anemic entity tests
├── usecases/                         # Use case orchestration + purity + session dispatch
├── services/                         # Interface contracts (+ multi-ref abstract method)
├── interfaces/                       # Protocol tests
├── config/                           # GitHubConfig + GitLabConfig (max_total_chars 600k)
├── factories/                        # Factory interface tests
├── test_error_codes.py
├── test_errors.py
├── test_exceptions.py
├── test_full_diff_incomplete_error.py  # E5020 + FullDiffIncompleteReason taxonomy
├── test_pr_diff_cache_v2.py            # Schema v2 keys / wrap / unwrap
├── test_gitlab_pr_diff_cache.py        # GitLab v1 identity builders + legacy rejection
├── test_vcs_provider_interface.py
└── test_vcs_provider_registry.py     # 601 — URL auto-detection
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **E5020 incomplete full-diff** | `test_full_diff_incomplete_error.py` | Reason enum (9 values), exception contract |
| **PRDiff cache v2** | `test_pr_diff_cache_v2.py` | `github_full_diff_v2_key`, wrap/unwrap |
| **GitLab cache identity** | `test_gitlab_pr_diff_cache.py` | Host-aware `gitlab-full-diff-v1` key/token/immutability |
| **GitLabConfig** | `config/test_gitlab_config.py` | Defaults, allowlist, `is_host_allowed` |
| **GitHubConfig defaults** | `config/test_github_config.py` | Size limits incl. `max_total_chars` 600k |
| **Strict identity entity** | `entities/test_pr_diff_cache.py` | `StrictPRDiffCacheIdentity` + GitHub identity |
| **Session vs legacy reader** | `usecases/test_session_pr_diff_usecase.py` | Session-capable PRDiff dispatch |
| **Entities** | `entities/` | `FilePatchInfo`, `FileDiffResponse.previous_path`, `PRDiff`, multi-ref content |
| **Multi-ref content types** | `entities/test_file_content_multi_ref.py` | `FileContentRequest`/`Response` identity |
| **Multi-ref API port** | `services/test_github_api_multi_ref_interface.py` | Abstract method required on interface |
| **Provider registry** | `test_vcs_provider_registry.py` | GitHub/GitLab URL routing |

## CONVENTIONS
- No network, no filesystem, no Dynaconf.
- Assert business methods on `FilePatchInfo` thoroughly.
- Keep use case tests on mocked ports (repository/service interfaces).
- Prefer frozen-instance / immutability checks for entities.

## ANTI-PATTERNS
- NO importing infrastructure from domain tests except when testing pure re-exports (prefer none).
- NO live provider clients.
- NO I/O or settings service in pure domain suites.
