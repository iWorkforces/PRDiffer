# AGENTS.md - Domain Entity Unit Tests

5 files, 1928 lines. FilePatchInfo (rich), PullRequest, Repository, PRDiff, FileDiffResponse.

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Business methods | `test_file_patch_info.py` → `TestFilePatchInfoMethods` |
| Computed properties | `test_file_patch_info.py` → `TestFilePatchInfoProperties` |
| Immutability | `test_pr_diff.py` → `TestPRDiffImmutability` |
| Serialization | `test_pr_diff.py` → `TestPRDiffSerialization` |
| Enum tests | Each file has `Test*Enum` class |

## CONVENTIONS

### Class Organization
`Test*Creation` → `Test*Properties` → `Test*Methods` → `Test*Enum` → `Test*Immutability` → `Test*Serialization`

### Entity Creation
```python
def test_entity_creation_minimal(self):  # Required fields, defaults
def test_entity_creation_full(self):     # All fields populated
```

### Business Methods (Rich Entities)
```python
def test_calculate_review_priority_high(self):
    patch = FilePatchInfo(filename="src/security/auth.py")
    assert patch.calculate_review_priority() == "high"
```

### Immutability (Frozen Dataclasses)
```python
def test_immutability_with_frozen(self):
    with pytest.raises(FrozenInstanceError):
        setattr(pr_diff, "files", ())
```

### Tuple for Frozen Fields
```python
pr_diff = PRDiff(files=(FileDiffResponse(...),))  # tuple, not list
```

## ANTI-PATTERNS

- ❌ `list` in frozen dataclass tests → Use `tuple`
- ❌ Missing `FrozenInstanceError` tests for frozen entities
- ❌ Mocking domain entities → Use real instances
- ❌ Missing edge cases (empty, None, zero)
