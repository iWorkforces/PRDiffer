# AGENTS.md - Integration Tests

End-to-end oriented tests (~2.5K lines, 7 test modules + helpers).

## STRUCTURE
```
tests/integration/
├── test_complete_workflow.py      # Full tool workflow (554)
├── test_error_scenarios.py        # Error paths (519)
├── test_security.py               # Security integration (731)
├── test_webhook_invalidation.py   # Cache invalidation (266)
├── test_real_github_api.py        # Optional real API (224)
├── test_server_launcher.py        # Process/launcher (98)
├── test_metrics_endpoint.py       # Metrics (77)
└── mcp_server_manual_test.py      # Manual harness helper
```

## CONVENTIONS
- Prefer fakes/mocks unless explicitly running real API tests.
- Mark slow/real-network tests appropriately if adding network dependency.
- Keep secrets out of fixtures; use env only for opt-in real API runs.

## ANTI-PATTERNS
- NO committing tokens.
- NO assuming network in default CI-less local runs.
