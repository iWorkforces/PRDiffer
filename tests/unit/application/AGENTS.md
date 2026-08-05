# AGENTS.md - Application Unit Tests

MCP server, tools, components, factories, and application utilities.

## STRUCTURE
```
tests/unit/application/
├── components/                    # Auth, rate limit, metrics, health, PR ops, config
├── factories/                     # ApplicationFactory tests
├── utils/                         # PR URL parser tests
├── test_tool_registry.py          # MCP tool registration/handlers (~724; E5020 ToolError JSON)
├── test_webhook_handler.py
├── test_health_endpoints.py
├── test_mcp_server_health_status.py
├── test_pr_url_validation.py
├── test_logging_safety.py
└── test_architecture.py
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **MCP tools** | `test_tool_registry.py` | `get_pr_diff`, `approve_pr`, `describe_pr`; E5020 → ToolError JSON |
| **PR URL multi-provider** | `utils/test_pr_url_parser.py` | `parse_pr_target` GitHub + GitLab (custom hosts) |
| **Auth / JWT / lockout** | `components/test_authentication.py` | Largest suite (1145) |
| **Webhooks** | `test_webhook_handler.py` | Cache invalidation orchestration |
| **Health / metrics HTTP** | `test_health_endpoints.py`, components | `/health`, metrics |
| **Layer checks** | `test_architecture.py` | Application layer expectations |

## CONVENTIONS
- Mock infrastructure ports and factories; focus on orchestration, auth gates, error translation — not domain math.
- Async tool paths: follow neighboring `@pytest.mark.asyncio` / anyio usage.
- Prefer `Mock(spec=...)` against domain Protocols where practical.

## ANTI-PATTERNS
- NO real HTTP server requirements for pure unit cases.
- NO live VCS API calls.
- NO business-logic assertions that belong in domain entity/use-case tests.
