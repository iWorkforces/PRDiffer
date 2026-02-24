"""Repository cache models and utilities."""

from dataclasses import dataclass
from functools import wraps
from typing import ParamSpec, TypeVar
from collections.abc import Callable

from prdiffer.domain.repositories import PRDiffRepositoryInterface

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class CacheEntry:
    """Data class representing a cache entry."""

    repository: PRDiffRepositoryInterface
    timestamp: float
    initialized: bool


def with_lock(lock_attr: str = "_lock") -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for automatic lock management."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            self = args[0]
            lock = getattr(self, lock_attr)
            with lock:
                return func(*args, **kwargs)

        return wrapper

    return decorator
