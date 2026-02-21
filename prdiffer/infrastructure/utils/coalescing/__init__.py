"""Request coalescing service for deduplicating concurrent requests."""

from prdiffer.infrastructure.utils.coalescing.service import (
    RequestCoalescingService,
    CoalescedRequest,
    get_request_coalescing_service,
    DEFAULT_MAX_WAITERS,
)

__all__ = [
    'RequestCoalescingService',
    'CoalescedRequest',
    'get_request_coalescing_service',
    'DEFAULT_MAX_WAITERS',
]
