---
name: Linting command
description: Run linting command and fix any issues found.
---

Your task is to run `./start-lint.sh --all` and analyze its output to identify code quality issues. Then fix all issues systematically, one by one.

## Process

1. Run the complete linting workflow:
   ```bash
   ./start-lint.sh --all
   ```

2. Review the output for linting issues such as:
   - Code style violations (PEP 8)
   - Unused imports or variables
   - Code complexity issues
   - Potential bugs or anti-patterns

3. Fix each issue:
   - Apply auto-fix suggestions where available
   - Manually resolve issues requiring code changes
   - Ensure fixes don't introduce new problems

4. Re-run the linter after each fix or batch of fixes to verify the resolution.

## Expected Output

The command uses Ruff and will report:
- File and line number of each issue
- Error code (e.g., F401, E501)
- Description of the issue
- Suggested fixes (when available)
