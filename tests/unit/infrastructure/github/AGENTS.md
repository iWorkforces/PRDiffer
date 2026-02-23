# AGENTS.md - GitHub Infrastructure Unit Tests

7 test files covering GitHub API client, file processor, diff generator, and mappers.

## OVERVIEW
Tests for GitHub API integration with PyGithub mocking. Comprehensive and basic test variants.

## STRUCTURE
```
tests/unit/infrastructure/github/
├── test_api_client.py                # Basic API client tests
├── test_api_client_comprehensive.py  # Full coverage (591 lines)
├── test_file_processor.py            # Basic file processing
├── test_file_processor_comprehensive.py  # Full coverage (556 lines)
├── test_diff_generator.py            # Basic diff generation
├── test_diff_generator_comprehensive.py  # Full coverage (743 lines)
└── test_github_mappers.py            # Domain model mapping
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| **API client** | `test_api_client_comprehensive.py` → retry, circuit breaker, rate limit |
| **File processing** | `test_file_processor_comprehensive.py` → chunking, filtering |
| **Diff generation** | `test_diff_generator_comprehensive.py` → unified diff, hunks |
| **Domain mapping** | `test_github_mappers.py` → PyGithub → Domain entities |

## CONVENTIONS

### PyGithub Mocking Pattern
```python
@pytest.fixture
def mock_github():
    '''Mock PyGithub hierarchy'''
    with patch('github.Github') as mock:
        mock_repo = Mock()
        mock_pr = Mock()
        mock_file = Mock()
        
        mock.return_value.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr
        mock_pr.get_files.return_value = [mock_file]
        
        yield mock

def test_get_pr_files(mock_github):
    client = GitHubAPIClient()
    files = client.get_pr_files('owner/repo', 123)
    assert len(files) == 1
```

### Comprehensive Test Pattern
- Basic tests: Happy path, single assertion
- Comprehensive tests: Edge cases, error handling, all branches

### Rate Limit Testing
```python
def test_rate_limit_handling(mock_github):
    '''Test 403/429 retry logic'''
    mock_github.return_value.get_repo.side_effect = [
        RateLimitExceededException(...),  # First call fails
        Mock()  # Retry succeeds
    ]
    # Verify retry happened
```

## ANTI-PATTERNS

- NO real GitHub API calls → Mock all PyGithub interactions
- NO testing PyGithub itself → Test our wrapper logic
- NO asyncio → Use @pytest.mark.anyio
- NO missing rate limit tests → Always test 403/429 handling
