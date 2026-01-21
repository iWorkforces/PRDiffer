# CLAUDE.md - Unit Tests: Domain Entities

This file provides guidance for working with unit tests for domain entities.

**Current Version:** 0.4.8

## Overview

Unit tests for domain entities verify the correctness of core business objects. Domain entities should have no external dependencies, making them straightforward to test.

## Test Files

Test files in this directory should test entities from `prdiffer/domain/entities/`:

- `test_file_patch.py` - Tests for `FilePatchInfo`
- `test_pr_diff.py` - Tests for `PRDiff`
- `test_edit_type.py` - Tests for `EDIT_TYPE` enum

## Writing Tests

### Test Structure

```python
"""Unit tests for [entity]."""

import pytest
from prdiffer.domain.entities import [Entity]

class Test[Entity]:
    """Unit tests for [Entity]."""

    def test_creation(self):
        """Test entity creation with valid data."""
        # Arrange
        data = {...}

        # Act
        entity = [Entity](**data)

        # Assert
        assert entity.field == expected_value

    def test_validation(self):
        """Test entity validates input data."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError):
            [Entity](invalid_data)

    def test_equality(self):
        """Test entity equality comparison."""
        # Arrange
        entity1 = [Entity](...)
        entity2 = [Entity](...)

        # Act & Assert
        assert entity1 == entity2

    def test_serialization(self):
        """Test entity can be serialized."""
        # Arrange
        entity = [Entity](...)

        # Act
        serialized = entity.model_dump()  # For Pydantic models
        # or
        serialized = asdict(entity)  # For dataclasses

        # Assert
        assert isinstance(serialized, dict)
```

### Best Practices

1. **No Mocking Needed**: Domain entities have no dependencies
2. **Test Validation**: Verify input validation works
3. **Test Equality**: Ensure equality operators work correctly
4. **Test Serialization**: Verify JSON/dict serialization
5. **Test Edge Cases**: Empty values, None, boundary conditions

## Running Tests

### Run All Entity Tests
```bash
# Using pytest
pytest tests/unit/domain/entities/ -v

# Using unittest script
./start-unittest.sh --run tests/unit/domain/entities/
```

### Run Specific Test File
```bash
# Using pytest
pytest tests/unit/domain/entities/test_file_patch.py -v

# Using unittest script
./start-unittest.sh --file tests/unit/domain/entities/test_file_patch.py
```

## Entity-Specific Testing

### FilePatchInfo Entity
Test the file change representation:
- **Creation**: Valid and invalid file patch data
- **Fields**: patch, filename, edit_type, num_lines, language
- **Edit Types**: ADDED, DELETED, MODIFIED, RENAMED, UNKNOWN
- **Statistics**: num_plus_lines, num_minus_lines
- **Optional Fields**: language, ai_file_summary
- **Edge Cases**: Empty patches, very long patches, special characters

### PRDiff Entity
Test the PR diff model:
- **Creation**: Valid PR diff data
- **Validation**: Required fields (url, number, title, diff_content)
- **Commit Messages**: List of commit messages
- **Serialization**: JSON output for MCP protocol
- **Edge Cases**: Empty diffs, no commits, special characters

### EDIT_TYPE Enum
Test the edit type enumeration:
- **Values**: ADDED, DELETED, MODIFIED, RENAMED, UNKNOWN
- **String Representation**: Correct display names
- **Validation**: Invalid values rejected
- **Conversion**: String to enum conversion

## Test Fixtures

Create reusable fixtures in `conftest.py`:

```python
# tests/unit/domain/entities/conftest.py

import pytest
from prdiffer.domain.entities import FilePatchInfo, PRDiff, EDIT_TYPE

@pytest.fixture
def sample_file_patch():
    """Sample file patch for testing."""
    return FilePatchInfo(
        patch="@@ -1,1 +1,2 @@\n-old\n+new",
        filename="test.py",
        edit_type=EDIT_TYPE.MODIFIED,
        num_plus_lines=1,
        num_minus_lines=1
    )

@pytest.fixture
def sample_pr_diff():
    """Sample PR diff for testing."""
    return PRDiff(
        url="https://github.com/owner/repo/pull/123",
        number=123,
        title="Test PR",
        diff_content="Full diff content",
        commit_messages=["Initial commit"]
)
```

## Dataclass vs Pydantic Models

Domain entities use both dataclasses and Pydantic models:

### Dataclass Testing (FilePatchInfo)
```python
def test_dataclass_equality():
    """Test dataclass equality."""
    patch1 = FilePatchInfo(...)
    patch2 = FilePatchInfo(...)
    assert patch1 == patch2

def test_dataclass_immutability():
    """Test dataclass is immutable (if frozen)."""
    patch = FilePatchInfo(...)
    with pytest.raises(Exception):  # FrozenInstanceError
        patch.filename = "new.py"
```

### Pydantic Model Testing (PRDiff)
```python
def test_pydantic_validation():
    """Test Pydantic model validation."""
    with pytest.raises(ValidationError):
        PRDiff(invalid_data)

def test_pydantic_serialization():
    """Test Pydantic model serialization."""
    pr_diff = PRDiff(...)
    json_data = pr_diff.model_dump_json()
    assert isinstance(json_data, str)
```

## Edge Cases to Test

### FilePatchInfo
- Empty patch string
- Very long filename (>255 chars)
- Special characters in filename
- Large line counts (>10000)
- Unknown edit type
- None values for optional fields

### PRDiff
- Empty commit messages list
- Very long diff content (>1MB)
- Special characters in title
- Invalid URLs
- Missing required fields

## Coverage

Ensure complete coverage for domain entities:

```bash
# Run with coverage
pytest tests/unit/domain/entities/ --cov=prdiffer.domain.entities --cov-report=html
```

**Target Coverage:** >90% for domain entities (they're simple and critical)

## Related Documentation

- `../CLAUDE.md` - Unit test documentation
- `../../../prdiffer/domain/entities/CLAUDE.md` - Entity documentation
- `../../../CLAUDE.md` - Project documentation
