# AGENTS.md - Infrastructure/Logging

Console logging and exception formatting (~436 lines).

## STRUCTURE
```
prdiffer/infrastructure/logging/
├── console_logger.py     # ConsoleLogger + get_logger (147)
├── exception_utils.py    # Safe exception serialization (284)
└── __init__.py
```

## CONVENTIONS
- Implement `LoggerServiceInterface` from domain.
- Never log tokens, API keys, or full secrets.
- Use structured fields where available; keep stdio transport safe (diagnostics off primary JSON-RPC stream).

## ANTI-PATTERNS
- NO print debugging in library paths that can break stdio MCP.
