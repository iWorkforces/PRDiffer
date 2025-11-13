"""MCP error mapper for Clean Architecture.

This component handles MCP-specific error mapping while delegating
business logic to the domain layer.
"""

from typing import Any, Dict
from abc import ABC, abstractmethod


class MCPErrorMapperInterface(ABC):
    """Abstract interface for MCP error mapping."""

    @abstractmethod
    def map_exception_to_mcp_error(self, exception: Exception) -> Dict[str, Any]:
        """Map a domain exception to an MCP-compatible error format.

        Args:
            exception: The exception to map

        Returns:
            Dict[str, Any]: MCP-compatible error format
        """
        pass

    @abstractmethod
    def map_validation_errors(self, errors: list) -> Dict[str, Any]:
        """Map validation errors to MCP-compatible format.

        Args:
            errors: List of validation errors

        Returns:
            Dict[str, Any]: MCP-compatible validation error format
        """
        pass


class MCPErrorMapper(MCPErrorMapperInterface):
    """Concrete MCP error mapper implementation."""

    def __init__(self, logger=None):
        """Initialize MCP error mapper.

        Args:
            logger: Optional logger for structured logging
        """
        self._logger = logger

    def map_exception_to_mcp_error(self, exception: Exception) -> Dict[str, Any]:
        """Map a domain exception to an MCP-compatible error format.

        Args:
            exception: The exception to map

        Returns:
            Dict[str, Any]: MCP-compatible error format
        """
        error_type = type(exception).__name__
        error_message = str(exception)

        if self._logger:
            self._logger.error(
                "Mapping exception to MCP error",
                error_type=error_type,
                error_message=error_message,
            )

        # Map specific exception types to MCP error categories
        error_category = self._get_error_category(exception)

        return {
            "type": error_category,
            "message": error_message,
            "details": {
                "exception_type": error_type,
                "exception_message": error_message,
            },
        }

    def map_validation_errors(self, errors: list) -> Dict[str, Any]:
        """Map validation errors to MCP-compatible format.

        Args:
            errors: List of validation errors

        Returns:
            Dict[str, Any]: MCP-compatible validation error format
        """
        if self._logger:
            self._logger.warning(
                "Mapping validation errors to MCP format",
                error_count=len(errors),
            )

        return {
            "type": "validation_error",
            "message": f"Validation failed with {len(errors)} error(s)",
            "details": {
                "error_count": len(errors),
                "errors": errors,
            },
        }

    def _get_error_category(self, exception: Exception) -> str:
        """Determine the error category based on exception type.

        Args:
            exception: The exception to categorize

        Returns:
            str: Error category for MCP protocol
        """
        exception_type = type(exception).__name__

        # Map common exception types to MCP error categories
        if "ValidationError" in exception_type:
            return "validation_error"
        elif "NotFoundError" in exception_type:
            return "not_found"
        elif "AuthenticationError" in exception_type:
            return "authentication_error"
        elif "AuthorizationError" in exception_type:
            return "authorization_error"
        elif "RateLimitError" in exception_type:
            return "rate_limit_exceeded"
        elif "TimeoutError" in exception_type:
            return "timeout"
        elif "ConnectionError" in exception_type:
            return "connection_error"
        elif "SuspiciousOperationError" in exception_type:
            return "security_error"
        elif "InputSanitizationError" in exception_type:
            return "input_error"
        else:
            return "internal_error"
