from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Callable


class RetryServiceInterface(ABC):
    """Interface for retry services with exponential backoff."""

    @abstractmethod
    def execute_with_retry(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function with retry logic and exponential backoff."""
        pass

    @abstractmethod
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an exception indicates a rate limit error."""
        pass
