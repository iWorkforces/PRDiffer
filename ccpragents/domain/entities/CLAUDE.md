# CLAUDE.md - Domain Entities

This file provides guidance for working with the domain entities of CCPRAgents.

## Overview

This directory contains the core business objects (entities) that represent the fundamental concepts in the CCPRAgents domain. These entities are pure data structures with no external dependencies, following Domain-Driven Design principles.

## Entities

### FilePatchInfo (`file_patch.py`)

**FilePatchInfo**
A dataclass representing a file change in a pull request, containing both the content and metadata about the change.

**Core Attributes:**
- `base_file: str` - Original file content (before changes)
- `head_file: str` - Modified file content (after changes) 
- `patch: str` - Unified diff string showing the changes
- `filename: str` - File path in the repository
- `edit_type: EDIT_TYPE` - Type of change (ADDED, DELETED, MODIFIED, RENAMED, UNKNOWN)
- `num_plus_lines: int` - Number of lines added
- `num_minus_lines: int` - Number of lines removed

**Extended Attributes:**
- `language: Optional[str]` - Programming language detected from file extension
- `ai_file_summary: Optional[str]` - AI-generated summary of the file changes

**EDIT_TYPE Enumeration:**
```python
class EDIT_TYPE(StrEnum):
    ADDED = "added"           # New file created
    DELETED = "deleted"       # File deleted
    MODIFIED = "modified"     # File content changed
    RENAMED = "renamed"       # File moved or renamed
    UNKNOWN = "unknown"       # Unrecognized change type
```

**Usage Pattern:**
```python
file_patch = FilePatchInfo(
    base_file="original content",
    head_file="modified content", 
    patch="@@ -1,3 +1,3 @@\n old\n+new\n",
    filename="src/main.py",
    edit_type=EDIT_TYPE.MODIFIED,
    num_plus_lines=1,
    num_minus_lines=1,
    language="python"
)
```

### PRDiff Models (`pr_diff.py`)

**PRDiff** (Base Model)
A Pydantic model representing basic pull request information.

**Core Attributes:**
- `pr_number: int` - Pull request number
- `repo_owner: str` - Repository owner/organization
- `repo_name: str` - Repository name
- `diff_content: str` - Combined diff content for all files
- `base_commit: str` - Base commit SHA
- `head_commit: str` - Head commit SHA
- `changed_files: int` - Number of files changed
- `additions: int` - Total lines added
- `deletions: int` - Total lines deleted

**ExtraPRDiff** (Extended Model)
Extends PRDiff with additional metadata and analysis.

**Additional Attributes:**
- `commit_messages: str` - Formatted commit messages from the PR
- `reviewers: List[str]` - List of PR reviewers (optional)
- `labels: List[str]` - PR labels (optional)
- `milestone: Optional[str]` - Associated milestone (optional)
- `created_at: Optional[str]` - PR creation timestamp (optional)
- `updated_at: Optional[str]` - Last update timestamp (optional)

**Pydantic Features:**
- **Validation**: Automatic field validation and type checking
- **Serialization**: JSON serialization/deserialization
- **Documentation**: Auto-generated schema documentation
- **Immutability**: Immutable objects after creation (by default)

**Usage Pattern:**
```python
pr_diff = ExtraPRDiff(
    pr_number=123,
    repo_owner="owner",
    repo_name="repository",
    diff_content="file diffs...",
    base_commit="abc123",
    head_commit="def456",
    changed_files=5,
    additions=150,
    deletions=75,
    commit_messages="1. Initial implementation\n2. Bug fixes",
    reviewers=["reviewer1", "reviewer2"],
    labels=["feature", "backend"]
)
```

## Design Principles

### Domain-Driven Design
- **Ubiquitous Language**: Entity names and attributes reflect domain terminology
- **Business Focus**: Entities represent business concepts, not technical implementation
- **Rich Domain Model**: Entities contain behavior and validation rules
- **Aggregate Roots**: PRDiff acts as an aggregate containing FilePatchInfo objects

### Clean Architecture
- **No External Dependencies**: Entities have no framework or infrastructure dependencies
- **Framework Agnostic**: Can be used with any framework or no framework
- **Testable**: Easy to test in isolation without mocking external services
- **Stable**: Changes to external systems don't affect entity structure

### Data Integrity
- **Immutability**: Entities are immutable by default to prevent accidental changes
- **Validation**: Pydantic models provide automatic validation and type checking
- **Consistency**: Entities maintain consistent state throughout their lifecycle
- **Type Safety**: Strong typing prevents runtime type errors

## Entity Relationships

### Composition Relationship
```
ExtraPRDiff (Aggregate Root)
    ├── Contains multiple FilePatchInfo objects
    ├── Provides PR-level metadata
    └── Coordinates file-level changes
```

### Data Flow
1. **Raw Data**: GitHub API returns repository and PR data
2. **Entity Creation**: Infrastructure layer creates entities from raw data
3. **Business Logic**: Use cases operate on entities
4. **Serialization**: Application layer serializes entities for output

## Validation Rules

### FilePatchInfo Validation
- `filename` must be non-empty string
- `edit_type` must be valid EDIT_TYPE enum value
- `num_plus_lines` and `num_minus_lines` must be non-negative
- `patch` should be valid unified diff format (when provided)

### PRDiff Validation
- `pr_number` must be positive integer
- `repo_owner` and `repo_name` must be non-empty strings
- `changed_files`, `additions`, `deletions` must be non-negative
- Commit SHAs should be valid Git SHA format (when provided)

### Custom Validation
Add custom validation using Pydantic validators:
```python
@validator('filename')
def validate_filename(cls, v):
    if not v or v.isspace():
        raise ValueError('filename cannot be empty')
    return v.strip()
```

## Serialization and Deserialization

### JSON Serialization
```python
# Serialize to JSON
pr_diff = ExtraPRDiff(...)
json_data = pr_diff.model_dump()
json_string = pr_diff.model_dump_json()

# Deserialize from JSON
pr_diff = ExtraPRDiff.model_validate(json_data)
pr_diff = ExtraPRDiff.model_validate_json(json_string)
```

### Schema Generation
```python
# Generate JSON schema
schema = ExtraPRDiff.model_json_schema()
```

## Testing Strategies

### Unit Testing Entities
```python
def test_file_patch_creation():
    patch = FilePatchInfo(
        base_file="old content",
        head_file="new content",
        patch="@@ diff",
        filename="test.py",
        edit_type=EDIT_TYPE.MODIFIED,
        num_plus_lines=1,
        num_minus_lines=1
    )
    assert patch.filename == "test.py"
    assert patch.edit_type == EDIT_TYPE.MODIFIED
```

### Validation Testing
```python
def test_pr_diff_validation():
    with pytest.raises(ValueError):
        PRDiff(
            pr_number=-1,  # Invalid: negative number
            repo_owner="",  # Invalid: empty string
            # ... other fields
        )
```

### Serialization Testing
```python
def test_pr_diff_serialization():
    original = ExtraPRDiff(...)
    json_data = original.model_dump()
    deserialized = ExtraPRDiff.model_validate(json_data)
    assert original == deserialized
```

## Extension Guidelines

### Adding New Attributes
1. **Domain Relevance**: Ensure new attributes represent domain concepts
2. **Backward Compatibility**: Use optional fields for new attributes
3. **Validation**: Add appropriate validation rules
4. **Documentation**: Update documentation and examples

### Creating New Entities
1. **Single Responsibility**: Each entity should represent one domain concept
2. **Rich Behavior**: Include domain logic and business rules
3. **Relationships**: Define clear relationships with existing entities
4. **Testing**: Comprehensive unit tests for all entity behavior

### Migration Considerations
When modifying entities:
- **Versioning**: Consider schema versioning for breaking changes
- **Migration Scripts**: Provide data migration utilities
- **Deprecation**: Gracefully deprecate old attributes
- **Documentation**: Update all relevant documentation

## File Organization

```
ccpragents/domain/entities/
├── __init__.py              # Public API exports
├── file_patch.py           # FilePatchInfo and EDIT_TYPE
└── pr_diff.py             # PRDiff and ExtraPRDiff models
```

## Performance Considerations

### Memory Usage
- **Large Diffs**: Consider streaming for very large PRs
- **Content Storage**: Balance between full content and patch-only storage
- **Batch Processing**: Process large collections of entities in batches

### Serialization Performance  
- **Field Selection**: Use `include`/`exclude` to serialize only needed fields
- **Custom Serializers**: Create custom serializers for performance-critical paths
- **Caching**: Cache serialized representations when appropriate

These entities form the stable core of the CCPRAgents domain model, providing a solid foundation for all business logic while maintaining flexibility for future enhancements.
