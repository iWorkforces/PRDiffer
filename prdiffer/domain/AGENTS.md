# AGENTS.md - Domain Layer

Pure business logic. No external deps, no I/O. Defines entities, interfaces, use cases, and factory contracts only.

## OVERVIEW
37 Python files (~3.4K lines). Frozen dataclasses for entities; ABC/Protocol for ports.

## STRUCTURE
```
prdiffer/domain/
├── entities/                 # PRDiff, FilePatchInfo, FileDiffResponse, PullRequest, Repository
├── services/                 # Service interfaces (ABC only; 9 ports)
├── usecases/                 # GetPRDiff, DescribePR, ApprovePR use cases
├── repositories/             # PRDiffRepositoryInterface
├── interfaces/               # VCS, input validation, coalescing, app Protocols
├── config/                   # GitHubConfig + interface
├── factories/                # ApplicationFactoryInterface, InfrastructureFactoryInterface
├── error_codes.py            # E1xxx–E5xxx constants
├── errors.py                 # ErrorCode, categories, MCPError helpers
├── exceptions.py             # PRDifferException hierarchy (455 lines)
└── vcs_provider_registry.py  # Multi-provider registry
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Rich domain model** | `entities/file_patch.py` | 329 lines; priority, smells, validate, stats |
| **MCP response shape** | `entities/file_diff_response.py`, `entities/pr_diff.py` | Frozen dataclasses (no Pydantic) |
| **Service interfaces** | `services/*.py` | ABC + `@abstractmethod` |
| **VCS provider contract** | `interfaces/vcs_provider.py` | `VCSDiffRepositoryInterface` |
| **App component Protocols** | `interfaces/protocols.py` | RateLimiter, Auth, Metrics, … |
| **Provider registry** | `vcs_provider_registry.py` | `supports_repository()` auto-detect |
| **Error codes** | `error_codes.py` + `errors.py` | Structured E-codes |
| **Factory contracts** | `factories/` | Dependency inversion for outer layers |

## CONVENTIONS

### Purity
- **NO imports from infrastructure/application**.
- No network, filesystem, Dynaconf, PyGithub, or logging backends.
- Enforce with `python3 scripts/analyze_dependencies.py --path prdiffer`.

### Entities
- Prefer `@dataclass(frozen=True)`.
- Use `tuple[T, ...]` for sequences (hashable).
- **Rich**: `FilePatchInfo` encapsulates review priority, code smells, validation.
- **Anemic/DTO**: `PRDiff`, `FileDiffResponse` hold structured response data.

### Interfaces
- Domain defines ports; infrastructure implements adapters.
- Protocols for application components live in `interfaces/protocols.py` so factories can depend on domain contracts.

### Error Model
- Exception hierarchy in `exceptions.py` (auth, rate limit, validation, not found, …).
- Parallel structured codes in `error_codes.py` / `errors.py` for MCP-facing responses.

## ANTI-PATTERNS
- **NO outer-layer imports** in domain.
- **NO I/O** in entities or use cases (inject ports, call from infrastructure/application).
- **NO concrete infrastructure types** as domain dependencies.
- **NO mutable dataclasses** for shared entities → `frozen=True`.
- **NO `list` fields on frozen dataclasses** → use `tuple`.
- **NO Pydantic in domain** → frozen dataclasses (current state: clean).

## NOTES
- Domain was previously documented as having Pydantic DTOs; `PRDiff` / `FileDiffResponse` are now frozen dataclasses.
