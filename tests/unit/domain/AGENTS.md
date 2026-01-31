# AGENTS.md - Domain Unit Tests

Pure business logic tests with no external dependencies or I/O.

## OVERVIEW
Test entities, service interfaces, use cases, and VCS provider contracts in isolation.

## STRUCTURE
```
tests/unit/domain/
├── entities/        # Pydantic/dataclass model tests
├── services/        # Interface contract tests (ABC/Protocol)
├── usecases/        # Business logic orchestration tests
└── test_vcs_provider_interface.py  # VCS provider contract validation
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Test entity** | `entities/` | Validate models, properties, business methods |
| **Test interface** | `services/` | Verify abstract methods, type hints |
| **Test use case** | `usecases/` | Pure business logic, no I/O |

## CONVENTIONS

### Entity Tests (Rich vs Anemic)
```python
def test_file_patch_info_validation():
    '''Test rich entity with business logic'''
    patch = FilePatchInfo(
        file_path='test.py',
        patch_lines=('line1', 'line2'),  # tuple, not list
        additions=10,
        deletions=5
    )
    
    # Test business methods
    assert patch.validate() == True
    assert patch.calculate_review_priority() > 0
    assert patch.total_changes == 15  # Property
```

### Frozen Dataclass Tests
```python
def test_frozen_dataclass_immutability():
    '''Test frozen dataclass with tuple fields'''
    config = GitHubConfig(
        rate_limit=5000,
        ignore_patterns=('*.lock', 'node_modules/'),  # tuple for hashability
    )
    
    # Verify frozen
    with pytest.raises(AttributeError):
        config.rate_limit = 10000
    
    # Verify hashable
    assert hash(config) is not None
```

### Interface Contract Tests
```python
def test_service_interface_abstract_methods():
    '''Verify interface requires implementation'''
    from prdiffer.domain.services import GitHubAPIServiceInterface
    
    # Should raise TypeError (missing abstract methods)
    with pytest.raises(TypeError):
        GitHubAPIServiceInterface()
```

### Use Case Tests (Pure Logic)
```python
@pytest.mark.unit
def test_get_pr_diff_use_case():
    '''Test use case orchestration (no I/O)'''
    # Mock dependencies
    github_service = Mock(spec=GitHubAPIServiceInterface)
    cache_service = Mock(spec=CacheServiceInterface)
    
    use_case = GetPRDiffUseCase(github_service, cache_service)
    
    # Test logic
    result = use_case.execute('https://github.com/owner/repo/pull/123')
    
    # Verify orchestration
    github_service.get_pr_diff.assert_called_once()
```

## ANTI-PATTERNS

- ❌ External imports (infrastructure/application) → Domain tests must be isolated
- ❌ I/O operations (files, network, DB) → No side effects
- ❌ Mocking domain entities → Use real instances (pure data)
- ❌ Production code in tests → Tests only
- ❌ Using `list` in frozen dataclass tests → Use `tuple`
- ❌ Missing immutability checks for frozen dataclasses
