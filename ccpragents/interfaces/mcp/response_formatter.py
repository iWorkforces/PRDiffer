"""MCP response formatter for Clean Architecture.

This component handles MCP-specific response formatting while delegating
business logic to the domain layer.
"""

from typing import Any, Dict
from abc import ABC, abstractmethod


class MCPResponseFormatterInterface(ABC):
    """Abstract interface for MCP response formatting."""

    @abstractmethod
    def format_success_response(self, result: Any) -> Dict[str, Any]:
        """Format a successful MCP tool response.

        Args:
            result: The result from the tool execution

        Returns:
            Dict[str, Any]: Formatted response for MCP protocol
        """
        pass

    @abstractmethod
    def format_error_response(self, error: Exception, tool_name: str) -> Dict[str, Any]:
        """Format an error response for MCP protocol.

        Args:
            error: The exception that occurred
            tool_name: Name of the tool that failed

        Returns:
            Dict[str, Any]: Formatted error response for MCP protocol
        """
        pass

    @abstractmethod
    def format_validation_error_response(
        self, errors: list, tool_name: str
    ) -> Dict[str, Any]:
        """Format a validation error response.

        Args:
            errors: List of validation errors
            tool_name: Name of the tool with validation errors

        Returns:
            Dict[str, Any]: Formatted validation error response
        """
        pass


class MCPResponseFormatter(MCPResponseFormatterInterface):
    """Concrete MCP response formatter implementation."""

    def __init__(self, logger=None):
        """Initialize MCP response formatter.

        Args:
            logger: Optional logger for structured logging
        """
        self._logger = logger

    def format_success_response(self, result: Any) -> Dict[str, Any]:
        """Format a successful MCP tool response.

        Args:
            result: The result from the tool execution

        Returns:
            Dict[str, Any]: Formatted response for MCP protocol
        """
        if self._logger:
            self._logger.debug(
                "Formatting successful MCP response",
                result_type=type(result).__name__,
            )

        return {
            "status": "success",
            "result": result,
            "error": None,
        }

    def format_error_response(self, error: Exception, tool_name: str) -> Dict[str, Any]:
        """Format an error response for MCP protocol.

        Args:
            error: The exception that occurred
            tool_name: Name of the tool that failed

        Returns:
            Dict[str, Any]: Formatted error response for MCP protocol
        """
        if self._logger:
            self._logger.error(
                "Formatting error MCP response",
                tool_name=tool_name,
                error=str(error),
                error_type=type(error).__name__,
            )

        return {
            "status": "error",
            "result": None,
            "error": {
                "message": str(error),
                "type": type(error).__name__,
                "tool": tool_name,
            },
        }

    def format_validation_error_response(
        self, errors: list, tool_name: str
    ) -> Dict[str, Any]:
        """Format a validation error response.

        Args:
            errors: List of validation errors
            tool_name: Name of the tool with validation errors

        Returns:
            Dict[str, Any]: Formatted validation error response
        """
        if self._logger:
            self._logger.warning(
                "Formatting validation error MCP response",
                tool_name=tool_name,
                error_count=len(errors),
            )

        return {
            "status": "validation_error",
            "result": None,
            "error": {
                "message": f"Validation failed with {len(errors)} error(s)",
                "type": "ValidationError",
                "tool": tool_name,
                "details": errors,
            },
        }
