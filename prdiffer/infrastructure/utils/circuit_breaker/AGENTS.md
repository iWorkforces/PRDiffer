# AGENTS.md - Circuit Breaker Package (Shim)

**Backward-compatibility shim.**

## CANONICAL MODULES
- `prdiffer.infrastructure.utils.circuit_breaker_core` — `CircuitState`, `CircuitBreaker`, `CircuitBreakerOpenException`
- `prdiffer.infrastructure.utils.circuit_breaker_registry` — `GlobalCircuitBreakerRegistry`, `get_global_circuit_breaker_registry`

## GUIDANCE
- New code imports canonical modules.
- Tests that reset module-level singletons should prefer the canonical registry module (shim notes document test reset pitfalls).
