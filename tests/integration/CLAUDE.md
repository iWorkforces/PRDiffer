# CLAUDE.md - Integration Tests

This file provides guidance for working with integration tests in PRDiffer.

**Current Version:** 0.4.7

## Overview

Integration tests verify that multiple components work together correctly. They test the interactions between layers and external services.

## Directory Structure

```
tests/integration/
├── CLAUDE.md                    # This file
├── __init__.py                  # Test package initialization
├── test_mcp_server.py          # MCP server integration tests
├── test_complete_workflow.py   # End-to-end workflow tests
├── test_error_scenarios.py     # Error handling tests
├── test_security.py            # Security validation tests
└── mcp_server_manual_test.py   # Manual MCP server testing
```

## Test Files

### test_mcp_server.py
Basic MCP server integration test.

**Purpose:** Verifies the MCP server can start up and respond to basic requests.

**Usage:**
```bash
# Run integration test
uv run python tests/test_mcp_server.py
```

### test_complete_workflow.py
Comprehensive end-to-end workflow tests.

**Purpose:** Tests the complete PR diff retrieval workflow from MCP request to response.

**Covers:**
- Full PR diff retrieval
- Caching behavior
- Error handling
- Rate limiting
- Multiple file processing

### test_error_scenarios.py
Error handling and edge case tests.

**Purpose:** Validates graceful error handling for various failure scenarios.

**Covers:**
- Invalid repository URLs
- Non-existent PRs
- Network failures
- API rate limits
- Malformed responses

### test_security.py
Security and input validation tests.

**Purpose:** Ensures security measures work correctly.

**Covers:**
- Input validation and sanitization
- SQL injection prevention
- Command injection prevention
- Path traversal prevention
- XSS attack prevention
- Token validation
- URL validation with security checks

### mcp_server_manual_test.py
Manual testing utility for MCP server.

**Purpose:** Interactive testing tool for development and debugging.

**Usage:**
```bash
# Run manual test server
uv run python tests/integration/mcp_server_manual_test.py
```

## Running Integration Tests

### Run All Integration Tests
```bash
# Using pytest
pytest tests/integration/ -v

# Using unittest
./start-unittest.sh --run tests/integration/
```

### Run Specific Test File
```bash
# Using pytest
pytest tests/integration/test_mcp_server.py -v

# Using unittest
./start-unittest.sh --file tests/integration/test_mcp_server.py
```

### Run Specific Test
```bash
# Using pytest
pytest tests/integration/test_complete_workflow.py::test_pr_diff_retrieval -v

# Using unittest
./start-unittest.sh --pattern test_pr_diff_retrieval
```

## Test Configuration

Integration tests require:
1. **GitHub Token**: Set `GITHUB_TOKEN` environment variable
2. **Test Repository**: Use a test repository for safe testing
3. **Network Access**: Tests make real GitHub API calls

**Setup:**
```bash
# Set GitHub token
export GITHUB_TOKEN="your_token_here"

# Or use .env file
echo "GITHUB_TOKEN=your_token_here" > .env
```

## Test Dependencies

Integration tests may use:
- Real GitHub API (requires token)
- Test repositories (public or private)
- Mocked external dependencies (when appropriate)
- Test fixtures and data

## Writing Integration Tests

### Test Structure

```python
"""Integration test for [feature]."""

import pytest
from prdiffer.application.factory import create_mcp_server

class TestFeatureIntegration:
    """Integration tests for [feature]."""

    @pytest.fixture
    async def server(self):
        """Create MCP server instance."""
        # Setup server with test configuration
        server = create_mcp_server(...)
        yield server
        # Cleanup

    @pytest.mark.asyncio
    async def test_feature_workflow(self, server):
        """Test complete feature workflow."""
        # Arrange
        # Set up test data

        # Act
        # Execute feature

        # Assert
        # Verify expected behavior
```

### Best Practices

1. **Use Real Dependencies**: Test with actual GitHub API when safe
2. **Isolate Tests**: Each test should be independent
3. **Clean Up**: Properly clean up resources after tests
4. **Use Fixtures**: Leverage pytest fixtures for common setup
5. **Mock When Necessary**: Mock expensive or unsafe operations
6. **Test Edge Cases**: Include error scenarios and edge cases

## Test Categories

### 1. Server Integration Tests
Test MCP server startup, tool registration, and request handling.

### 2. API Integration Tests
Test GitHub API integration with real API calls.

### 3. Workflow Tests
Test complete workflows from request to response.

### 4. Error Handling Tests
Test error scenarios and recovery.

### 5. Security Tests
Test security measures and input validation.

## Continuous Integration

Integration tests run in CI/CD pipeline:
1. On every pull request
2. Before merging to main
3. On scheduled builds

**CI Configuration:**
- GitHub token provided as secret
- Test repositories used for safe testing
- Tests run with timeout limits
- Failed tests block merging

## Debugging Integration Tests

### Enable Verbose Output
```bash
pytest tests/integration/ -vv -s
```

### Run with Debugger
```bash
pytest tests/integration/test_mcp_server.py --pdb
```

### View Logs
Integration tests produce detailed logs:
```bash
# Run with log output
pytest tests/integration/ --log-cli-level=DEBUG
```

### Common Issues

**GitHub API Rate Limit:**
- Use authenticated requests
- Implement rate limit handling
- Use test repositories with higher limits

**Network Issues:**
- Implement retries with exponential backoff
- Use appropriate timeouts
- Handle connection errors gracefully

**Test Data Issues:**
- Use dedicated test repositories
- Clean up test data after tests
- Avoid modifying production data

## Performance Testing

Integration tests can include performance benchmarks:
```python
def test_pr_diff_performance(benchmark):
    """Benchmark PR diff retrieval performance."""
    result = benchmark(get_pr_diff, owner, repo, pr_number)
    assert result is not None
```

## Related Documentation

- `../unit/CLAUDE.md` - Unit test documentation
- `../../prdiffer/CLAUDE.md` - Package structure
- `../../README.md` - Project overview
