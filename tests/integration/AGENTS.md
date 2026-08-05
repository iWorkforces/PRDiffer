# AGENTS.md - Integration Tests

End-to-end oriented tests (~2.6K lines, 8 test modules + manual helper).

## STRUCTURE
```
tests/integration/
├── test_complete_workflow.py      # Full tool workflow (554)
├── test_error_scenarios.py        # Error paths (519)
├── test_security.py               # Security integration (731)
├── test_webhook_invalidation.py   # Cache invalidation (266)
├── test_full_diff_mcp_surface.py  # Strict full-diff FastMCP surface (141)
├── test_real_github_api.py        # Optional real API (224)
├── test_server_launcher.py        # Process/launcher (98)
├── test_metrics_endpoint.py       # Metrics (77)
└── mcp_server_manual_test.py      # Manual harness helper
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Strict full-diff MCP contract** | `test_full_diff_mcp_surface.py` | In-process FastMCP; `get_pr_diff` success + E5020 failure surface; rename `previous_path` |
| **Tool workflow** | `test_complete_workflow.py` | End-to-end tool orchestration with mocks |
| **Attack / injection paths** | `test_security.py` | Marked `integration` |
| **Webhook cache bust** | `test_webhook_invalidation.py` | Invalidation + error bodies |
| **Opt-in live GitHub** | `test_real_github_api.py` | Requires real token/env; not for default CI |

## CONVENTIONS
- Prefer fakes/mocks unless explicitly running real API tests.
- Mark with `@pytest.mark.integration` (and `@pytest.mark.anyio` where async FastMCP surface needs it).
- Keep secrets out of fixtures; use env only for opt-in real API runs.
- Default local/CI path must not require network.

## ANTI-PATTERNS
- NO committing tokens or API keys.
- NO assuming network in default CI or local runs.
- NO placing pure unit cases here when they belong under `tests/unit/`.
