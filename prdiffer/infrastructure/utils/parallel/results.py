"""Result types and error handling strategies for parallel execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")
K = TypeVar("K")
R = TypeVar("R")


class ErrorStrategy(str, Enum):
    IGNORE = "ignore"  # Log errors, return only successful results
    RAISE = "raise"  # Raise first exception encountered
    COLLECT = "collect"  # Return both successful results and errors
    CONTINUE = "continue"  # Continue processing, return detailed batch results


@dataclass
class BatchResult(Generic[T]):
    successful: list[T] = field(default_factory=list)
    failed: list[tuple[Any, Exception]] = field(default_factory=list)

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


@dataclass(frozen=True)
class IndexedItemOutcome(Generic[K, R]):
    """Immutable outcome for one submitted batch item, keyed by index/identity."""

    index: int
    key: K
    value: R | None = None
    error: BaseException | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class IndexedBatchResult(Generic[K, R]):
    """Indexed batch outcomes in submission order (never compacted)."""

    outcomes: tuple[IndexedItemOutcome[K, R], ...]

    @property
    def values_in_order(self) -> tuple[R, ...]:
        """Return successful values only when the entire batch succeeded."""
        if any(not outcome.ok for outcome in self.outcomes):
            raise IndexedBatchError(
                "Cannot read values from a failed indexed batch",
                outcomes=self.outcomes,
            )
        values: list[R] = []
        for outcome in self.outcomes:
            if outcome.value is None:
                raise IndexedBatchError(
                    "Successful outcome missing value",
                    outcomes=self.outcomes,
                )
            values.append(outcome.value)
        return tuple(values)

    @property
    def failed_outcomes(self) -> tuple[IndexedItemOutcome[K, R], ...]:
        return tuple(outcome for outcome in self.outcomes if not outcome.ok)

    @property
    def all_succeeded(self) -> bool:
        return all(outcome.ok for outcome in self.outcomes)


class IndexedBatchError(Exception):
    """Raised when a strict indexed batch fails; carries full ordered outcomes."""

    def __init__(
        self,
        message: str,
        *,
        outcomes: tuple[IndexedItemOutcome[Any, Any], ...],
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.outcomes: tuple[IndexedItemOutcome[Any, Any], ...] = outcomes
        self.failed: tuple[IndexedItemOutcome[Any, Any], ...] = tuple(o for o in outcomes if not o.ok)
        if cause is not None:
            self.__cause__ = cause

    @property
    def first_failure(self) -> IndexedItemOutcome[Any, Any] | None:
        """First non-cancellation failure when present; else first failure."""
        for outcome in self.failed:
            if outcome.error is not None and type(outcome.error).__name__ not in {
                "CancelledError",
                "CancelledException",
            }:
                return outcome
        return self.failed[0] if self.failed else None
