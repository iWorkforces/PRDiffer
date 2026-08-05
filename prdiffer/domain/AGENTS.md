# AGENTS.md - Domain Layer

Pure business logic. No external deps, no I/O. Entities, ports (ABC/Protocol), use cases, and factory contracts only.

## OVERVIEW
Package **0.6.0**, Python **3.14.3+**, branch `enhance-stability`.  
~34 non-`__init__` modules across root + 7 subpackages. Frozen dataclasses for most entities; ABC/Protocol for ports.

## STRUCTURE
```
prdiffer/domain/
├── entities/                 # PRDiff, FilePatchInfo (329), FileDiffResponse, content/cache types
├── services/                 # Service interfaces (ABC only; 9 ports)
├── usecases/                 # GetPRDiff (session + legacy), DescribePR, ApprovePR
├── repositories/             # PRDiffRepositoryInterface
├── interfaces/               # VCS, PRDiffReader session, input validation, coalescing, app Protocols
├── config/                   # GitHubConfig + GitHubConfigInterface
├── factories/                # ApplicationFactoryInterface, InfrastructureFactoryInterface
├── error_codes.py            # E1xxx–E5xxx constants (~386), incl. E5020_FULL_DIFF_INCOMPLETE
├── errors.py                 # ErrorCode, MCPError helpers (~218)
├── exceptions.py             # PRDifferException hierarchy (~562); FullDiffIncompleteError
└── vcs_provider_registry.py  # VCSProviderRegistry (~110)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Rich domain model** | `entities/file_patch.py` | 329 lines; priority, smells, validate, stats |
| **MCP response shape** | `entities/file_diff_response.py`, `entities/pr_diff.py` | Frozen dataclasses; `previous_path` on renames |
| **Typed content** | `entities/file_content.py` | `FileContentAvailable` / `FileContentUnavailable` |
| **Generated diff unit** | `entities/generated_file_diff.py` | `GeneratedFileDiff` (index, path, previous_path, diff) |
| **Full-diff cache v2** | `entities/pr_diff_cache.py` | `PRDiffCacheEntryV2`, `github-full-diff-v2` keys |
| **Session PR path** | `interfaces/pr_diff_reader.py` + `usecases/pr_diff_usecases.py` | Session reader vs legacy two-call path |
| **Service interfaces** | `services/*.py` | ABC + `@abstractmethod` |
| **VCS provider contract** | `interfaces/vcs_provider.py` | `VCSDiffRepositoryInterface` |
| **App component Protocols** | `interfaces/protocols.py` | RateLimiter, Auth, Metrics, Health, … (~180) |
| **Provider registry** | `vcs_provider_registry.py` | `supports_repository()` auto-detect |
| **Error codes** | `error_codes.py` + `errors.py` | Structured E-codes |
| **Full-diff incomplete** | `exceptions.py` | `FullDiffIncompleteError` + `FullDiffIncompleteReason` |
| **GitHub config VO** | `config/github_config.py` | Size limits, request timeout, parallel flags default `false` |
| **Factory contracts** | `factories/` | Dependency inversion for outer layers |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `PRDiff` | Entity | `entities/pr_diff.py` | `files: tuple[FileDiffResponse, ...]` |
| `FileDiffResponse` | Entity | `entities/file_diff_response.py` | path/status/stats/diff/`previous_path` |
| `FilePatchInfo` | Entity | `entities/file_patch.py` | Rich review model (329) |
| `FileContentAvailable` / `Unavailable` | Entity | `entities/file_content.py` | Typed content acquisition |
| `GeneratedFileDiff` | Entity | `entities/generated_file_diff.py` | One generated full-context file |
| `PRDiffCacheEntryV2` | Entity | `entities/pr_diff_cache.py` | Strict full-diff cache schema v2 |
| `SessionPRDiffReader` | Protocol | `interfaces/pr_diff_reader.py` | `open_pr_diff_session` |
| `GetPRDiffUseCase` | Use case | `usecases/pr_diff_usecases.py` | Session path (~61–100) vs legacy |
| `E5020_FULL_DIFF_INCOMPLETE` | ErrorCode | `error_codes.py` | Full-diff incompleteness |
| `FullDiffIncompleteError` | Exception | `exceptions.py` | Maps to E5020; safe details only |
| `GitHubConfig` | Config VO | `config/github_config.py` | Frozen; full-diff admission limits |
| `VCSProviderRegistry` | Registry | `vcs_provider_registry.py` | Multi-provider URL selection |

## CONVENTIONS

### Purity
- **NO imports from infrastructure/application**.
- No network, filesystem, Dynaconf, PyGithub, or logging backends.
- Enforce with `python3 scripts/analyze_dependencies.py --path prdiffer`.

### Entities
- Prefer `@dataclass(frozen=True)` (`PRDiff`, `FileDiffResponse`, content/cache types).
- Use `tuple[T, ...]` for sequences (hashable).
- **Rich**: `FilePatchInfo` — review priority, code smells, validation.
- **Anemic/DTO**: `PRDiff`, `FileDiffResponse` hold structured response data.
- Note: `PullRequest` / `Repository` use non-frozen `@dataclass` (mutable value objects).

### Interfaces
- Domain defines ports; infrastructure implements adapters.
- Application component Protocols live in `interfaces/protocols.py` so factories depend on domain contracts.
- GitHub full-diff uses session ports (`SessionPRDiffReader`); GitLab keeps legacy `PRDiffReader` methods.

### Error Model
- Exception hierarchy in `exceptions.py` (auth, rate limit, validation, not found, cache, config, processing, security, …).
- Parallel structured codes in `error_codes.py` / `errors.py` for MCP-facing responses (`MCPError` family).
- **Strict full-diff incompleteness**: `E5020_FULL_DIFF_INCOMPLETE` + `FullDiffIncompleteError(GitHubAPIError)` with `FullDiffIncompleteReason`:
  - `INVENTORY_TRUNCATED`, `FILE_COUNT_LIMIT`, `BINARY_CONTENT`, `FILE_SIZE_LIMIT`, `CONTENT_UNAVAILABLE`, `CONTENT_DECODE_FAILED`, `UNSUPPORTED_FILE_STATUS`, `DIFF_GENERATION_FAILED`, `RESPONSE_SIZE_LIMIT`
  - Safe details only: `reason`, `path`, `previous_path`, `observed`, `limit` — never tokens or raw content.
- Do **not** remap auth/permission/rate-limit/retry-exhausted network failures to E5020; unexpected algorithm defects stay `E5003_DIFF_GENERATION_ERROR`.

### Full-diff correctness (0.6.0)
- Success responses are complete by construction (no completeness boolean).
- `FileDiffResponse.previous_path` only for `EDIT_TYPE.RENAMED`.
- Content union: available empty text ≠ deterministic unavailability; operational failures raise.
- Cache: versioned `github-full-diff-v2` keys; ignore unversioned/v1/wrong-schema on read.

## ANTI-PATTERNS
- **NO outer-layer imports** in domain.
- **NO I/O** in entities or use cases (inject ports; adapters live outside).
- **NO concrete infrastructure types** as domain dependencies.
- **NO mutable shared entities** where frozen is expected → prefer `frozen=True` + `tuple`.
- **NO `list` fields on frozen dataclasses** → use `tuple`.
- **NO Pydantic in domain** → frozen dataclasses.
- **NO leaking raw content/tokens** in `FullDiffIncompleteError.details`.

## NOTES
- Domain has no package `__init__` re-exports at root; import concrete modules.
- Dual error surfaces: `exceptions.PRDifferException` (domain ops) and `errors.MCPError` (MCP response shaping).
