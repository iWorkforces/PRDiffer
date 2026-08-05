# AGENTS.md - Infrastructure/Security

**Package:** 0.6.0  
Input validation, injection detection, and sanitization (~961 lines).

## STRUCTURE
```
prdiffer/infrastructure/security/
├── input_validator.py            # InputValidator + helpers mixin (326)
├── input_validation_helpers.py   # Shared validation helpers (279)
├── injection_detector.py         # SecurityPatterns + InjectionDetector (216)
└── sanitizer.py                  # InputSanitizer (140)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Validate PR URL / params** | `input_validator.py` | Orchestrates checks; domain `InputValidatorProtocol` |
| **Module-level helpers** | `input_validation_helpers.py` | Token, branch, path, PR number helpers |
| **Threat patterns** | `injection_detector.py` | Command, path traversal, SQL-ish |
| **Sanitize for logs** | `sanitizer.py` | Length-limited safe strings |

## CONVENTIONS
- Implements `InputValidatorProtocol` (domain).
- Configurable patterns may come from settings.
- Fail closed on suspicious input with domain validation errors / **E1xxx** codes.
- Prefer orchestration through `InputValidator` rather than calling detector/sanitizer ad hoc from tools.

## ANTI-PATTERNS
- NO auth decisions based only on client-supplied claims without API keys.
- NO regex ReDoS-prone patterns without review.
- NO trusting unsanitized free-text for logs or shell/path construction.
- NO disabling injection checks for convenience in production paths.
