# AGENTS.md - Application Unit Tests

MCP server, tools, components, and application utilities.

## STRUCTURE
```
tests/unit/application/
├── components/                    # Auth, rate limit, metrics, health, PR ops, config
├── factories/                     # ApplicationFactory tests
├── utils/                         # PR URL parser tests
├── test_tool_registry.py          # MCP tool registration/handlers (592)
├── test_webhook_handler.py
├── test_health_endpoints.py
├── test_mcp_server_health_status.py
├── test_pr_url_validation.py
├── test_logging_safety.py
└── test_architecture.py
```

## CONVENTIONS
- Mock infrastructure ports and factories.
- Focus on orchestration, auth gates, error translation — not domain math.

## ANTI-PATTERNS
- NO real HTTP server requirements for pure unit cases.
