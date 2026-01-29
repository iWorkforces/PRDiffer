# Implementation Instructions for Task 1.2

## Files to Modify

1. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/application/mcp_server.py`
   - Replace approve_pr classmethod validation (lines 609-620) with instance validator call
   - Remove redundant boolean check and exception handling

2. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/application/components/pr_operation_handler.py`
   - Replace _parse_pr_url method to use InputValidator instance
   - Add import for InputValidator if not present

3. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/infrastructure/github_repository.py`
   - Replace parse_github_pr_url usage with InputValidator.validate_github_url
   - Remove url_parser import if no longer needed

4. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/infrastructure/factories/infrastructure_factory.py`
   - Update create_pr_operation_handler to inject InputValidator instance

5. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/infrastructure/security/input_validator.py`
   - Add validate_github_url method that calls parse_github_pr_url from url_parser
   - Keep existing suspicious-pattern and length checks

6. `/Volumes/Data/GitHub/cc/PRDifferMCP/prdiffer/application/components/authentication.py`
   - Add validate_token method (or update validate_api_key_format to delegate to InputValidator.validate_token)

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

1. Modify InputValidator (add validate_github_url method)
2. Create test_pr_url_validation.py
3. Update mcp_server.py approve_pr
4. Update pr_operation_handler.py _parse_pr_url
5. Update github_repository.py approve_pr_with_comment
6. Update infrastructure_factory.py
7. Update authentication.py validate_api_key_format
8. Update test_authentication.py
9. Run pytest verification

## Verification

After implementation:
```bash
pytest tests/unit/application/test_pr_url_validation.py -q
pytest tests/unit/application/components/test_authentication.py -q
```