# Task 3.3: Refactor Code Duplication - Implementation Plan

**Started**: 2026-01-30
**Status**: In Progress

## Scope

### 3.3a: Consolidate `_get_logger()` Duplication
**Files affected**:
- `prdiffer/infrastructure/utils/retry_handler.py:511-522` (12 lines)
- `prdiffer/infrastructure/utils/diff_utils.py:66-75` (10 lines)

**Approach**:
1. Create `prdiffer/infrastructure/utils/logger_factory.py` with shared implementation
2. Update both files to import and use shared function
3. Keep thread-safe double-check locking pattern
4. Add unit tests for logger_factory.py

### 3.3b: Consolidate PR URL Parsing
**Files affected**:
- `prdiffer/application/utils/pr_url_parser.py::parse_pr_url()` (59 lines, uses InputValidator)
- `prdiffer/infrastructure/utils/url_parser.py::parse_github_pr_url()` (146 lines, no InputValidator)

**Analysis**:
- `parse_pr_url()` delegates to `InputValidator.validate_github_url()` (comprehensive security checks)
- `parse_github_pr_url()` does manual regex parsing (duplicate logic with InputValidator)

**Decision**:
- Keep `parse_pr_url()` as canonical implementation (uses InputValidator)
- Deprecate `parse_github_pr_url()` in `url_parser.py`
- Add redirect from `parse_github_pr_url()` to `parse_pr_url()` for backward compatibility
- Check all usages and migrate to `parse_pr_url()`

### 3.3c: Retry Handler Sync/Async Duplication (Optional - Assess First)
**File**: `prdiffer/infrastructure/utils/retry_handler.py` (864 lines)
**Classes**:
- `UnifiedRetryHandler` - sync version (line 671)
- Has both `execute_with_retry()` and `execute_with_retry_async()` methods

**Assessment needed**:
- Check if there's significant code duplication between sync/async implementations
- If >90% identical, extract common logic to base class
- If not, document decision to keep separate

## Execution Order

1. ✅ 3.3a: Logger consolidation (low risk, high value)
2. ✅ 3.3b: PR URL parser consolidation (medium effort, clear win)
3. ✅ 3.3c: Retry handler assessment (assess, decide if worth refactoring)

## Success Criteria

- [x] Single implementation of `_get_logger()` pattern
- [x] Single canonical PR URL parser
- [x] All callers updated to use shared code
- [x] Tests verify shared utilities work correctly
- [x] Linting passes
- [x] Type checking passes
- [x] All existing tests pass
- [x] Documentation updated
