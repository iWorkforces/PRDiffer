# Implementation Instructions for Task 1.2

## Files to Modify

1. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/application/mcp_server.py`
   - Replace approve_pr classmethod validation (lines 609-620) with instance validator call
   - Remove redundant boolean check and exception handling

2. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/application/components/pr_operation_handler.py`
   - Replace _parse_pr_url method to use InputValidator instance
   - Add import for InputValidator if not present

3. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/infrastructure/github_repository.py`
   - Replace parse_github_pr_url import and usage with InputValidator.validate_github_url
   - Remove url_parser import if no longer needed

4. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/infrastructure/factories/infrastructure_factory.py`
   - Update create_pr_operation_handler to inject InputValidator instance

5. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/infrastructure/security/input_validator.py`
   - Add validate_github_url method that calls parse_github_pr_url from url_parser
   - This provides unified URL parsing + validation through InputValidator

6. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/application/components/authentication.py`
   - Add validate_token method to InputValidator (API key format centralization)
   - Update validate_api_key_format to delegate to InputValidator.validate_token

## Test Files to Create

1. `/Volumes/Data/GitHub/cc/PRDifferMCP/tests/unit/application/test_pr_url_validation.py` (NEW)
   - Test valid GitHub PR URLs (pull/ and pulls/)
   - Test invalid URLs (wrong host, missing components, malformed)
   - Test non-GitHub URLs
   - Test malformed PR numbers

2. `/Volumes/Data/GitHub/cc/PRDifferMCP/tests/unit/application/components/test_authentication.py` (UPDATE)
   - Add tests for validate_token method
   - Ensure API key format rules are enforced

## Implementation Order

1. Modify InputValidator (add methods)
2. Update mcp_server.py (approve_pr)
3. Update pr_operation_handler.py (_parse_pr_url)
4. Update github_repository.py (approve_pr_with_comment)
5. Update infrastructure_factory.py (inject InputValidator)
6. Update authentication.py (validate_token delegation)
7. Create test_pr_url_validation.py
8. Update test_authentication.py (add token tests)
9. Run tests to verify

## Verification

After implementation:
```bash
pytest tests/unit/application/test_pr_url_validation.py -v
pytest tests/unit/application/components/test_authentication.py -v
```
