"""Result types and error handling strategies for parallel execution."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar, Generic, Any

T = TypeVar("T")
R = TypeVar("R")


class ErrorStrategy(str, Enum):
    """Error handling strategy for parallel execution."""

    IGNORE = "ignore"  # Log errors, return only successful results
    RAISE = "raise"  # Raise first exception encountered
    COLLECT = "collect"  # Return both successful results and errors
    CONTINUE = "continue"  # Continue processing, return detailed batch results


@dataclass
class BatchResult(Generic[T]):
    """Result of a batch execution with success/failure tracking."""

    successful: list[T] = field(default_factory=lambda: [])
    failed: list[tuple[Any, Exception]] = field(default_factory=lambda: [])

    @property
    def total(self) -> int:
        """Total number of items processed."""
        return len(self.successful) + len(self.failed)

    @property
    def success_count(self) -> int:
        """Number of successful items."""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Number of failed items."""
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if self.total == 0:
            return 100.0
        return (self.success_count / self.total) * 100

    @property
    def all_succeeded(self) -> bool:
        """Check if all items succeeded."""
        return len(self.failed) == 0

    def get_errors(self) -> list[Exception]:
        """Get list of all exceptions."""
        return [error for _, error in self.failed]
