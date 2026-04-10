"""Circuit breaker registry for managing multiple circuit breakers.

BACKWARD COMPATIBILITY SHIM: This module has been flattened.
The canonical location is now ``prdiffer.infrastructure.utils.circuit_breaker_registry``.
"""

from prdiffer.infrastructure.utils.circuit_breaker_registry import (
    GlobalCircuitBreakerRegistry,
    get_global_circuit_breaker_registry,
)

# Re-export the module-level singleton variable for backward compatibility.
# Tests may reset this directly (e.g., ``cb_registry._global_circuit_breaker_registry = None``).
# We need to import it so the attribute exists on this module, but note that
# resetting it on this shim module won't affect the canonical module's variable.
# The canonical module's get_global_circuit_breaker_registry() checks this shim
# module to detect such resets.

__all__ = [
    "GlobalCircuitBreakerRegistry",
    "get_global_circuit_breaker_registry",
]
