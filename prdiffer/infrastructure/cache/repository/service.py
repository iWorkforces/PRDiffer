"""Repository cache service.

BACKWARD COMPATIBILITY SHIM: This module has been flattened.
The canonical location is now ``prdiffer.infrastructure.cache.cache_repository``.
"""

from prdiffer.infrastructure.cache.cache_repository import (
    RepositoryCacheService,
    get_repository_cache_service,
)

__all__ = [
    "RepositoryCacheService",
    "get_repository_cache_service",
]
