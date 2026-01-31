# AGENTS.md - Domain Layer

Pure business logic. No external deps, no I/O, defines interfaces only.

## STRUCTURE
```
prdiffer/domain/
├── entities/       # Core business objects (FilePatchInfo, PRDiff)
├── services/       # Service interfaces (abstract only)
├── usecases/       # Business logic orchestration
├── repositories/    # Data access contracts
├── interfaces/     # Protocol definitions (VCSDiffRepositoryInterface)
├── config/         # Configuration interfaces
├── factories/      # Factory patterns for dependency inversion
└── vcs_provider_registry.py  # Multi-provider registry
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Rich domain model** | `entities/file_patch.py` | 414 lines, business methods |
| **Service interfaces** | `services/*.py` | ABC with @abstractmethod |
| **VCS provider contract** | `interfaces/vcs_provider.py` | VCSDiffRepositoryInterface |
| **Provider registry** | `vcs_provider_registry.py` | Auto-detect from URL |
| **Exception hierarchy** | `exceptions.py`, `errors.py` | PRDifferException base |
| **Factory contracts** | `factories/infrastructure_factory.py` | Dependency inversion |

## CONVENTIONS

### Interface-Implementation Separation
- Domain defines interfaces only (ABC/Protocol)
- Infrastructure implements in outer layer
- **NO imports from infrastructure/application** → Domain must remain pure
- Strict enforcement via `scripts/analyze_dependencies.py`

### Rich vs Anemic Entities
- **Rich entity:** FilePatchInfo (350+ lines, 14 methods, 9 properties)
  - Encapsulates business logic: `validate()`, `detect_code_smells()`, `calculate_review_priority()`
  - Preferred for complex domain logic
- **Anemic entity:** PRDiff (data container only)
  - Simple data holder with no behavior
  - Use for DTOs and simple value objects

### Frozen Dataclasses
- Always `@dataclass(frozen=True)` for immutability
- Use `tuple[T, ...]` for sequences (hashability)
- **Never use `list` in frozen dataclasses** → Not hashable
- Example: `file_patches: tuple[FilePatchInfo, ...]`

### Factory Pattern
- InfrastructureFactoryInterface for dependency inversion
- Abstract factory methods for service creation
- Return interfaces, not concrete types
- Dual factory pattern: domain interfaces, infrastructure implements

### VCS Provider Registry
- Register providers implementing VCSDiffRepositoryInterface
- Auto-select from URL via `supports_repository()`
- Multi-provider: GitHub, GitLab, Bitbucket (extensible)

## ANTI-PATTERNS

- **NO external imports** → Domain must remain pure (14 violations currently exist)
- **NO I/O operations** → File/network calls in infrastructure
- **NO concrete implementations** → Only ABC/Protocol in domain
- **NO PyGithub/requests** → Use interfaces, import in infrastructure
- **NO anemic entities everywhere** → Rich models preferred for business logic
- **NO mutable dataclasses** → Always frozen=True
- **NO list in frozen dataclasses** → Use tuple for hashability
