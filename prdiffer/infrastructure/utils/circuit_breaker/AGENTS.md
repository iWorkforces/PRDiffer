# AGENTS.md - Circuit Breaker Package (Shim)

**Package:** 0.6.0  
**Backward-compatibility shim.**

## CANONICAL MODULES
- `prdiffer.infrastructure.utils.circuit_breaker_core` (215) — `CircuitState`, `CircuitBreaker`, `CircuitBreakerOpenException`
- `prdiffer.infrastructure.utils.circuit_breaker_registry` (271) — `GlobalCircuitBreakerRegistry`, `get_global_circuit_breaker_registry`

## STRUCTURE
```
prdiffer/infrastructure/utils/circuit_breaker/
├── __init__.py
├── core.py        # re-exports from circuit_breaker_core
└── registry.py    # re-exports from circuit_breaker_registry
```

## GUIDANCE
- New code imports **canonical** modules (`circuit_breaker_core` / `circuit_breaker_registry`).
- State machine: CLOSED → OPEN → HALF_OPEN.
- Tests that reset module-level singletons should prefer the canonical registry module (shim/canonical dual references can leave stale globals if only one is cleared).

## ANTI-PATTERNS
- NO second divergent CB implementation inside the shim package.
- NO bypassing the breaker for external API calls when it is integrated on the client path.
