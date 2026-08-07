"""Request coalescing service implementation.

BACKWARD COMPATIBILITY SHIM: This module has been flattened.
The canonical location is ``prdiffer.infrastructure.utils.coalescing_service``.
"""

from prdiffer.infrastructure.utils.coalescing_service import (
    DEFAULT_MAX_WAITERS,
    CoalescedRequest,
    RequestCoalescingService,
    get_request_coalescing_service,
)

__all__ = [
    "DEFAULT_MAX_WAITERS",
    "CoalescedRequest",
    "RequestCoalescingService",
    "get_request_coalescing_service",
]
