"""Circuit breaker utilities for fault tolerance.

This package provides a thread-safe circuit breaker implementation that prevents
cascading failures by temporarily stopping calls to a failing service.

Modules:
- core: CircuitState, CircuitBreaker, CircuitBreakerOpenException
- registry: GlobalCircuitBreakerRegistry for managing multiple breakers
"""

from prdiffer.infrastructure.utils.circuit_breaker.core import (
    CircuitState,
    CircuitBreaker,
    CircuitBreakerOpenException,
)
from prdiffer.infrastructure.utils.circuit_breaker.registry import (
    GlobalCircuitBreakerRegistry,
    get_global_circuit_breaker_registry,
)

__all__ = [
    # Core
    "CircuitState",
    "CircuitBreaker",
    "CircuitBreakerOpenException",
    # Registry
    "GlobalCircuitBreakerRegistry",
    "get_global_circuit_breaker_registry",
]
