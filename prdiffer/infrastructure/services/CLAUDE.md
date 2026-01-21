# CLAUDE.md - Infrastructure Services

This file provides guidance for working with the infrastructure service implementations in PRDiffer.

**Current Version:** 0.4.8

## Overview

The `services/` directory contains concrete implementations of domain service interfaces. These services provide the actual business logic implementation using infrastructure components like GitHub API clients, diff generators, and file processors.

## Key Components

### GitHubPRDiffService (`pr_diff_service.py`)

Concrete implementation of `PRDiffServiceInterface` that provides PR diff operations using the GitHub API.

**Constructor Parameters:**
```python
def __init__(
    self,
    github_api_client: Optional[GitHubAPIServiceInterface] = None,
    diff_generator: Optional[DiffGenerator] = None,
    file_processor: Optional[FileProcessor] = None,
    logger: Optional[LoggerServiceInterface] = None,
):
```

**Interface Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `get_pr_diff(repo_owner, repo_name, pr_number)` | Fetches complete PR diff data | `Optional[PRDiff]` |
| `get_latest_commit_sha(repo_owner, repo_name, pr_number)` | Gets latest commit SHA | `Optional[str]` |
| `validate_repository_access(repo_owner, repo_name)` | Validates repository accessibility | `bool` |

**Internal Methods:**
- `_generate_diff_content()` - Generates unified diff content for all files
- `_get_base_commit_sha()` - Finds the base commit for comparison
- `_get_commit_messages()` - Extracts formatted commit messages
- `_convert_github_files_to_file_patch_info()` - Converts GitHub file objects to domain entities
- `_map_github_status_to_edit_type()` - Maps GitHub status strings to `EDIT_TYPE` enum

## File Structure

```
prdiffer/infrastructure/services/
├── __init__.py               # Package initialization
├── pr_diff_service.py        # GitHubPRDiffService implementation
└── CLAUDE.md                 # This file
```

## Processing Pipeline

The `get_pr_diff()` method follows this workflow:

```
1. Repository Access
   ├── Get repository via GitHub API client
   └── Get pull request object

2. Diff Generation
   ├── Get latest commit SHA
   ├── Get base commit SHA (merge base)
   ├── Get PR files list
   └── Process files through FileProcessor or fallback

3. Content Generation
   ├── Generate extended diff via DiffGenerator
   └── Or fallback to simple patch-based diff

4. Result Assembly
   └── Create PRDiff entity with diff_content and commit_messages
```

## Dependencies

The service integrates with these components:

```
GitHubPRDiffService
├── GitHubAPIClient (GitHubAPIServiceInterface)
│   ├── get_repository()
│   └── get_pull_request()
├── DiffGenerator
│   ├── generate_extended_diff()
│   └── get_commit_messages()
├── FileProcessor
│   └── process_files_to_patches()
└── ConsoleLogger (LoggerServiceInterface)
```

## Error Handling

The service implements graceful degradation:

```python
async def get_pr_diff(self, repo_owner, repo_name, pr_number) -> Optional[PRDiff]:
    try:
        # ... processing logic
        return pr_diff
    except Exception as e:
        self._logger.error(
            "Failed to get PR diff",
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None
```

**Error Strategies:**
- Returns `None` on failure instead of raising exceptions
- Logs errors with full context for debugging
- Falls back to simpler processing when components unavailable

## EDIT_TYPE Mapping

GitHub file status is mapped to domain enum:

| GitHub Status | EDIT_TYPE |
|---------------|-----------|
| `"added"` | `EDIT_TYPE.ADDED` |
| `"removed"` | `EDIT_TYPE.DELETED` |
| `"modified"` | `EDIT_TYPE.MODIFIED` |
| `"renamed"` | `EDIT_TYPE.RENAMED` |
| Other | `EDIT_TYPE.UNKNOWN` |

## Configuration

The service uses environment variables for initialization:

```python
github_token = os.getenv("GITHUB_TOKEN")
timeout = int(os.getenv("GITHUB_TIMEOUT", "30"))

self._github_api.initialize_client(github_token=github_token, timeout=timeout)
```

## Development Guidelines

### Adding New Methods

1. Define method in `PRDiffServiceInterface` (domain layer)
2. Implement method in `GitHubPRDiffService`
3. Add appropriate error handling and logging
4. Return domain entities or primitives, not GitHub objects

### Error Handling Best Practices

- Catch specific exceptions when possible
- Log with structured context (`repo_owner=`, `pr_number=`)
- Return `None` or empty values for graceful degradation
- Include `error_type` in logs for easier debugging

### Testing

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_get_pr_diff():
    # Create mocks
    mock_api = Mock(spec=GitHubAPIServiceInterface)
    mock_api.get_repository.return_value = mock_repo
    mock_api.get_pull_request.return_value = mock_pr

    # Create service with mocks
    service = GitHubPRDiffService(
        github_api_client=mock_api,
        diff_generator=mock_diff_gen,
        file_processor=mock_file_proc,
        logger=mock_logger,
    )

    # Test
    result = await service.get_pr_diff("owner", "repo", 123)
    assert result is not None
```

## Integration Points

- **Domain Layer**: Implements `PRDiffServiceInterface`
- **Infrastructure Factory**: Created by `InfrastructureFactory.create_pr_diff_service()`
- **GitHub Components**: Uses `GitHubAPIClient`, `DiffGenerator`, `FileProcessor`
- **Logging**: Uses `LoggerServiceInterface` for structured logging

## Usage Example

```python
from prdiffer.infrastructure.services.pr_diff_service import GitHubPRDiffService
from prdiffer.infrastructure.github.api_client import GitHubAPIClient
from prdiffer.infrastructure.github.diff_generator import get_diff_generator
from prdiffer.infrastructure.github.file_processor import FileProcessor

# Create service with dependencies
service = GitHubPRDiffService(
    github_api_client=GitHubAPIClient(),
    diff_generator=get_diff_generator(diff_utils=DiffUtils()),
    file_processor=FileProcessor(...),
    logger=get_logger(),
)

# Use service
pr_diff = await service.get_pr_diff("owner", "repo", 123)
if pr_diff:
    print(pr_diff.diff_content)
    print(pr_diff.commit_messages)
```

## Notes

- The service is async-first (`async def get_pr_diff`)
- Fallback behavior exists when optional components are missing
- Full file content is fetched for accurate diff generation
- Commit messages are formatted with numbered list
