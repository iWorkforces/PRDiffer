"""Retry service interface for domain layer."""

from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Callable


class RetryServiceInterface(ABC):
    """Abstract base class for retry services.

    This interface defines the contract for services that provide
    retry logic with exponential backoff for operations that may fail.
    """

    @abstractmethod
    def execute_with_retry(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function with retry logic and exponential backoff.

        Args:
            func: Function to execute with retry logic
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the successful function call

        Raises:
            Exception: If all retry attempts fail
        """
        pass

    @abstractmethod
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an exception indicates a rate limit error.

        Args:
            error: Exception to check

        Returns:
            bool: True if this is a rate limit error, False otherwise
        """
        pass
