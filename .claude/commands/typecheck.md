---
name: Python static type check command
description: Run static type check command and fix any issues found.
---

Your task is to run `./start-type-check.sh` and analyze its output to identify type checking issues. Then fix all issues systematically, one by one.

## Process

1. Run the type check command:
   ```bash
   ./start-type-check.sh
   ```

2. Review the output for type errors, missing annotations, or type mismatches.

3. Fix each issue:
   - Add missing type hints
   - Correct incorrect type annotations
   - Resolve type compatibility issues

4. Re-run the type check after each fix or batch of fixes to verify the resolution.

## Expected Output

The command uses `ty` (Type-checked Python) and will report:
- File and line number of each issue
- Type error description
- Suggested fixes (when available)
