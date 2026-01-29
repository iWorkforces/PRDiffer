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
- No imports from infrastructure in domain

### Rich Entities
- FilePatchInfo: business methods (`validate()`, `detect_code_smells()`, `calculate_review_priority()`)
- PRDiff: simple data holder (anemic) vs FilePatchInfo (rich)
- Encapsulate domain rules within entities

### Factory Pattern
- InfrastructureFactoryInterface for dependency inversion
- Abstract factory methods for service creation
- Return interfaces, not concrete types

### VCS Provider Registry
- Register providers implementing VCSDiffRepositoryInterface
- Auto-select from URL via `supports_repository()`
- Multi-provider: GitHub, GitLab, Bitbucket (extensible)

## ANTI-PATTERNS

- **NO external imports** → Domain must remain pure
- **NO I/O operations** → File/network calls in infrastructure
- **NO concrete implementations** → Only ABC/Protocol in domain
- **NO PyGithub/requests** → Use interfaces, import in infrastructure
- **NO anemic entities everywhere** → Rich models preferred for business logic
