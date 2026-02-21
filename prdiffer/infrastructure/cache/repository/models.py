"""Repository cache models and utilities."""

from dataclasses import dataclass
from functools import wraps
from typing import Callable

from prdiffer.infrastructure.github_repository import GitHubPRDiffRepository


@dataclass
class CacheEntry:
    """Data class representing a cache entry."""

    repository: GitHubPRDiffRepository
    timestamp: float
    initialized: bool


def with_lock(lock_attr: str = "_lock"):
    """Decorator for automatic lock management."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            lock = getattr(self, lock_attr)
            with lock:
                return func(self, *args, **kwargs)

        return wrapper

    return decorator
