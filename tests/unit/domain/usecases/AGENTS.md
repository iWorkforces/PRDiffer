# AGENTS.md - Domain Use Cases Unit Tests

3 test files covering business logic orchestration: PR diff, PR description, PR approval use cases.

## OVERVIEW
Pure business logic tests with no I/O. Tests verify orchestration flow and domain rules.

## STRUCTURE
```
tests/unit/domain/usecases/
├── test_pr_diff_usecases.py      # GetPRDiffUseCase, diff generation
├── test_pr_description_usecases.py  # PR description retrieval
└── test_pr_approval_usecases.py  # PR approval workflow
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| **Diff retrieval** | `test_pr_diff_usecases.py` → `TestGetPRDiffUseCase` |
| **Description** | `test_pr_description_usecases.py` → `TestGetPRDescription` |
| **Approval** | `test_pr_approval_usecases.py` → `TestApprovePRUseCase` |

## CONVENTIONS

### Use Case Test Pattern
```python
@pytest.fixture
def use_case():
    '''Create use case with mocked services'''
    github_service = Mock(spec=GitHubAPIServiceInterface)
    cache_service = Mock(spec=CacheServiceInterface)
    return GetPRDiffUseCase(github_service, cache_service)

def test_use_case_orchestration(use_case):
    '''Test the orchestration flow'''
    # Setup mocks
    use_case.github_service.get_pr_diff.return_value = mock_diff
    
    # Execute
    result = use_case.execute(pr_url)
    
    # Verify orchestration
    use_case.github_service.get_pr_diff.assert_called_once()
    assert result == expected_result
```

### Cache Interaction Testing
```python
def test_use_case_caching(use_case):
    '''Test cache check/store flow'''
    use_case.cache_service.get.return_value = cached_result
    
    result = use_case.execute(pr_url)
    
    # Should return cached, not call GitHub
    use_case.github_service.get_pr_diff.assert_not_called()
```

### Error Propagation Testing
```python
def test_use_case_error_propagation(use_case):
    '''Test domain exceptions bubble up'''
    use_case.github_service.get_pr_diff.side_effect = RepositoryNotFoundError()
    
    with pytest.raises(RepositoryNotFoundError):
        use_case.execute(pr_url)
```

## ANTI-PATTERNS

- NO I/O operations → Mock all services
- NO infrastructure imports → Use domain interfaces only
- NO business logic in mocks → Test real orchestration
- NO testing service internals → Test use case behavior
