# AGENTS.md - Infrastructure/Security

Input validation, injection detection, sanitization (~961 lines).

## STRUCTURE
```
prdiffer/infrastructure/security/
├── input_validator.py            # InputValidator + helpers mixin (326)
├── input_validation_helpers.py   # Shared helpers (279)
├── injection_detector.py         # SecurityPatterns + InjectionDetector (216)
├── sanitizer.py                  # InputSanitizer (140)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Validate PR URL / params** | `input_validator.py` | Orchestrates checks |
| **Threat patterns** | `injection_detector.py` | Command, path traversal, SQL-ish |
| **Sanitize for logs** | `sanitizer.py` | Length-limited safe strings |

## CONVENTIONS
- Implements `InputValidatorProtocol` (domain).
- Configurable patterns may come from settings.
- Fail closed on suspicious input with domain validation errors / E1xxx codes.

## ANTI-PATTERNS
- NO auth decisions based only on client-supplied claims without keys.
- NO regex ReDoS-prone patterns without review.
