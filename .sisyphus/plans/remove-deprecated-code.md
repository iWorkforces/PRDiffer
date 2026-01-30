# Deprecated Code Removal Plan

**Project:** PRDifferMCP  
**Created:** 2026-01-30  
**Estimated Effort:** 4-5 weeks  
**Impact:** ~1,500-2,000 lines to clean  
**Status:** In Progress

---

## Priority 1: Active Deprecations & Unused Config (Week 1)

### 1.1 Remove Deprecated InfrastructureFactory Methods
**File:** `prdiffer/infrastructure/factories/infrastructure_factory.py` (lines 206-321)

- [ ] Search for all usages of `InfrastructureFactory.create_rate_limiter()`
- [ ] Search for all usages of `InfrastructureFactory.create_metrics_tracker()`
- [ ] Search for all usages of `InfrastructureFactory.create_pr_operation_handler()`
- [ ] Search for all usages of `InfrastructureFactory.create_health_monitor()`
- [ ] Search for all usages of `InfrastructureFactory.create_server_configuration()`
- [ ] Search for all usages of `InfrastructureFactory.create_authentication()`
- [ ] Replace all usages with `ApplicationFactory` equivalents
- [ ] Remove the 6 deprecated methods from `infrastructure_factory.py`
- [ ] Update tests to use `ApplicationFactory`
- [ ] Run test suite to verify
- [ ] Run type check to verify
- [ ] Commit changes

**Verification:**
```bash
./start-unittest.sh --run
./start-type-check.sh --check
./start-lint.sh --all
```

### 1.2 Remove Unused Configuration Keys
**File:** `settings.toml`

- [ ] Remove JWT settings (5 entries): `jwt.secret`, `jwt.algorithm`, `jwt.expires_in`, `jwt.audience`, `jwt.issuer`
- [ ] Remove circuit breaker registry settings (3 entries)
- [ ] Remove file processing settings: `max_file_size_mb`, `chunk_size_kb`
- [ ] Remove auth settings: `max_failures_per_minute`, `lockout_duration`, `failure_window`
- [ ] Remove API health settings: `window_size`, `time_window`
- [ ] Remove other unused settings (5 more)
- [ ] Verify no code references removed settings
- [ ] Run test suite to verify
- [ ] Commit changes

**Verification:**
```bash
grep -r "jwt\.secret" prdiffer/ tests/
grep -r "circuit_breaker_registry" prdiffer/ tests/
./start-unittest.sh --run
```

### 1.3 Remove Deprecated Test Module
**File:** `tests/unit/infrastructure/utils/test_cache_decorator.py` (301 lines)

- [ ] Verify no other tests depend on this file
- [ ] Remove entire test file
- [ ] Run test suite to verify
- [ ] Commit changes

**Verification:**
```bash
./start-unittest.sh --run --coverage
```

### 1.4 Remove Skipped Deprecated Tests
**File:** `tests/test_phase2_improvements.py` (lines 203-268)

- [ ] Remove `test_process_files_with_content_parallel_basic()`
- [ ] Remove `test_process_files_with_content_parallel_rate_limiting()`
- [ ] Run test suite to verify
- [ ] Commit changes

---

## Priority 2: Type Hint Modernization (Weeks 2-3)

### 2.1 Update Infrastructure Layer (33 files)
**Pattern:** Replace `from typing import List, Dict, Optional, Union, Tuple, Set` with Python 3.14+ built-ins

**High-priority files (10+ type imports):**
- [ ] `prdiffer/infrastructure/async_parallel_executor.py` (10 type imports)
- [ ] `prdiffer/infrastructure/utils/retry_handler.py` (9 type imports)
- [ ] `prdiffer/infrastructure/utils/cache_decorator.py` (7 type imports)
- [ ] `prdiffer/infrastructure/github/api_client.py` (7 type imports)

**Medium-priority files (5-9 type imports):**
- [ ] `prdiffer/infrastructure/github/file_processor.py` (5 type imports)
- [ ] `prdiffer/infrastructure/di_container.py`
- [ ] `prdiffer/infrastructure/cache_service.py`
- [ ] `prdiffer/infrastructure/security/input_validator.py`
- [ ] `prdiffer/infrastructure/security/injection_detector.py`
- [ ] 20+ more infrastructure files

**Replacement rules:**
- `List[T]` → `list[T]`
- `Dict[K, V]` → `dict[K, V]`
- `Optional[T]` → `T | None`
- `Union[A, B]` → `A | B`
- `Tuple[T, ...]` → `tuple[T, ...]`
- `Set[T]` → `set[T]`

**Verification after each batch:**
```bash
./start-type-check.sh --check
./start-lint.sh --all
./start-unittest.sh --run
```

### 2.2 Update Domain Layer (30 files)
- [ ] Update all domain entities
- [ ] Update all domain interfaces
- [ ] Update all domain use cases
- [ ] Run type check and tests

### 2.3 Update Application Layer (15 files)
- [ ] Update MCP server components
- [ ] Update plugin system
- [ ] Update tool registry
- [ ] Run type check and tests

### 2.4 Update Tests (75+ files)
- [ ] Update unit tests
- [ ] Update integration tests
- [ ] Run full test suite with coverage

---

## Priority 3: Anti-Patterns & Refactoring (Week 4)

### 3.1 Replace asyncio with anyio in Tests
**4 test files to update:**

- [ ] `tests/test_github_client.py` (line 4)
  - Replace `import asyncio` with `import anyio`
  - Replace `asyncio.run()` with `anyio.run()`
  
- [ ] `tests/integration/test_error_scenarios.py` (line 138)
  - Replace asyncio primitives with anyio equivalents
  
- [ ] `tests/unit/domain/usecases/test_pr_approval_usecases.py`
  - Replace asyncio mocks with anyio
  
- [ ] `tests/unit/infrastructure/test_async_parallel_executor.py` (line 8)
  - Replace asyncio usage with anyio

**Verification:**
```bash
grep -r "import asyncio" tests/
./start-unittest.sh --run
```

### 3.2 Remove Legacy Server Constructor
**File:** `prdiffer/application/factory.py` (lines 112-129)

- [ ] Search for usages of `create_mcp_server_legacy()`
- [ ] Replace with modern `create_mcp_server()`
- [ ] Remove `create_mcp_server_legacy()` method
- [ ] Run tests to verify
- [ ] Commit changes

### 3.3 Handle NotImplementedError Stubs
**File:** `prdiffer/application/components/pr_operation_handler.py` (lines 209-278)

**Option A: Remove if truly unused**
- [ ] Search for calls to `describe_pr()`, `approve_pr()`, `review_pr()`, `update_pr_changelog()`
- [ ] If unused, remove all 4 methods
- [ ] Update protocol interface in `prdiffer/domain/interfaces/protocols.py`

**Option B: Implement if needed**
- [ ] Implement `describe_pr()` functionality
- [ ] Implement `approve_pr()` functionality
- [ ] Implement `review_pr()` functionality
- [ ] Implement `update_pr_changelog()` functionality
- [ ] Add tests for new implementations

**Decision needed:** Check usage first

### 3.4 Refactor Large Complex Files (Optional)
**Candidates for refactoring (>500 lines):**

- [ ] `retry_handler.py` (848 lines) → Split into modules
- [ ] `api_client.py` (771 lines) → Extract request/response handlers
- [ ] `github_repository.py` (709 lines) → Split by responsibility
- [ ] `authentication.py` (673 lines) → Extract auth strategies

**Note:** This is optional and can be deferred to a separate refactoring effort.

---

## Priority 4: Documentation & Cleanup (Week 5)

### 4.1 Update Documentation
- [ ] Update `AGENTS.md` to remove references to deprecated patterns
- [ ] Update `README.md` if needed
- [ ] Update any inline documentation mentioning old patterns
- [ ] Commit documentation changes

### 4.2 Final Verification
- [ ] Run full test suite: `./start-unittest.sh --run`
- [ ] Run coverage check: `./start-unittest.sh --coverage` (maintain >70%)
- [ ] Run type check: `./start-type-check.sh --check`
- [ ] Run linting: `./start-lint.sh --all`
- [ ] Review all commits for consistency

### 4.3 Update AGENTS.md
- [ ] Remove "Old-Style Typing Imports" from anti-patterns section
- [ ] Remove references to deprecated factory methods
- [ ] Update "Commands" section if needed
- [ ] Update code map if major changes occurred

---

## Rollback Plan

If any phase breaks tests or causes issues:

1. **Revert the problematic commit:**
   ```bash
   git revert <commit-hash>
   ```

2. **Re-run verification:**
   ```bash
   ./start-unittest.sh --run
   ./start-type-check.sh --check
   ```

3. **Document the issue** and adjust plan

4. **Retry with smaller scope** or different approach

---

## Success Criteria

- ✅ All deprecated methods removed
- ✅ All unused configuration removed
- ✅ All type hints modernized to Python 3.14+ style
- ✅ All tests use anyio instead of asyncio
- ✅ All tests passing
- ✅ Type checking passes with no errors
- ✅ Linting passes with no warnings
- ✅ Code coverage maintained at >70%
- ✅ No regressions in functionality
- ✅ AGENTS.md updated to reflect changes

---

## Notes

- **Commit strategy:** Small, atomic commits for each logical change
- **Testing strategy:** Run tests after each major change
- **Risk mitigation:** Keep changes isolated to single files when possible
- **Documentation:** Update inline comments as code changes
- **Review:** Self-review each change before committing

---

## Progress Tracking

**Started:** 2026-01-30  
**Current Phase:** Priority 1 - Active Deprecations  
**Completed Tasks:** 0 / ~100+  
**Estimated Completion:** TBD
