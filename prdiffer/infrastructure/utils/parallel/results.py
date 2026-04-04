"""Result types and error handling strategies for parallel execution."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar, Generic, Any

T = TypeVar("T")


class ErrorStrategy(str, Enum):
    IGNORE = "ignore"  # Log errors, return only successful results
    RAISE = "raise"  # Raise first exception encountered
    COLLECT = "collect"  # Return both successful results and errors
    CONTINUE = "continue"  # Continue processing, return detailed batch results


@dataclass
class BatchResult(Generic[T]):
    successful: list[T] = field(default_factory=lambda: [])
    failed: list[tuple[Any, Exception]] = field(default_factory=lambda: [])

    @property
    def total(self) -> int:
        return len(self.successful) + len(self.failed)

    @property
    def success_count(self) -> int:
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.success_count / self.total) * 100

    @property
    def all_succeeded(self) -> bool:
        return len(self.failed) == 0

    def get_errors(self) -> list[Exception]:
        return [error for _, error in self.failed]
