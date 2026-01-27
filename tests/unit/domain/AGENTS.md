# AGENTS.md - Domain Unit Tests

Pure business logic tests with no external dependencies.

## OVERVIEW
Test entities, service interfaces, use cases, and VCS provider contracts.

## STRUCTURE
```
tests/unit/domain/
├── entities/        # Pydantic model tests
├── services/        # Interface contract tests
├── usecases/        # Business logic tests
└── test_vcs_provider_interface.py  # Interface validation
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| **Test entity** | `entities/` | Validate Pydantic models |
| **Test interface** | `services/` or `test_vcs_provider_interface.py` | Verify abstract methods |
| **Test use case** | `usecases/` | Pure business logic |

## CONVENTIONS

### Entity Tests
- Validate Pydantic BaseModel instantiation
- Test Field validation and constraints
- Verify property method behavior

### Interface Tests
- Use ABC to verify required abstract methods
- Type hint validation
- No implementation logic

### Use Case Tests
- Pure logic only (no I/O, no external deps)
- Input/output validation
- State transitions

## ANTI-PATTERNS

- **NO external imports** → Domain layer tests must be isolated
- **NO I/O operations** → No files, no network, no DB
- **NO mocking external services** → Use fakes or contracts
- **NO production code** → Tests only
