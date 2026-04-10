"""Circuit breaker core implementation.

BACKWARD COMPATIBILITY SHIM: This module has been flattened.
The canonical location is now ``prdiffer.infrastructure.utils.circuit_breaker_core``.
"""

from prdiffer.infrastructure.utils.circuit_breaker_core import (
    CircuitState,
    CircuitBreaker,
    CircuitBreakerOpenException,
)

__all__ = [
    "CircuitState",
    "CircuitBreaker",
    "CircuitBreakerOpenException",
]
