"""MCP request validator for Clean Architecture.

This component handles MCP-specific request validation while delegating
security validation to the domain layer.
"""

from typing import Any, Dict
from abc import ABC, abstractmethod

from ccpragents.domain.services.logger import LoggerServiceInterface


class MCPRequestValidatorInterface(ABC):
    """Abstract interface for MCP request validation."""

    @abstractmethod
    def validate_tool_parameters(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> bool:
        """Validate parameters for an MCP tool call.

        Args:
            tool_name: Name of the tool
            parameters: Parameters to validate

        Returns:
            bool: True if parameters are valid, False otherwise
        """
        pass

    @abstractmethod
    def sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize MCP tool parameters.

        Args:
            parameters: Raw parameters from MCP client

        Returns:
            Dict[str, Any]: Sanitized parameters
        """
        pass


class MCPRequestValidator(MCPRequestValidatorInterface):
    """Concrete MCP request validator implementation."""

    def __init__(self, logger: LoggerServiceInterface):
        """Initialize MCP request validator.

        Args:
            logger: Logger service for structured logging
        """
        self._logger = logger

    def validate_tool_parameters(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> bool:
        """Validate parameters for an MCP tool call.

        Args:
            tool_name: Name of the tool
            parameters: Parameters to validate

        Returns:
            bool: True if parameters are valid, False otherwise
        """
        # Basic MCP parameter validation
        if not isinstance(parameters, dict):
            self._logger.warning(
                "Invalid MCP parameters format",
                tool_name=tool_name,
                parameters_type=type(parameters).__name__,
            )
            return False

        # Tool-specific validation
        if tool_name == "get_pr_diff":
            return self._validate_get_pr_diff_parameters(parameters)
        elif tool_name == "health":
            return True  # Health tool has no parameters
        else:
            self._logger.warning("Unknown MCP tool", tool_name=tool_name)
            return False

    def _validate_get_pr_diff_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate parameters for get_pr_diff tool.

        Args:
            parameters: Parameters for get_pr_diff tool

        Returns:
            bool: True if parameters are valid, False otherwise
        """
        # Check required parameter
        if "pr_url" not in parameters:
            self._logger.warning(
                "Missing required parameter for get_pr_diff",
                required_parameter="pr_url",
            )
            return False

        pr_url = parameters["pr_url"]

        # Basic type validation
        if not isinstance(pr_url, str):
            self._logger.warning(
                "Invalid parameter type for get_pr_diff",
                parameter_name="pr_url",
                expected_type="str",
                actual_type=type(pr_url).__name__,
            )
            return False

        # Basic format validation (detailed validation done by domain layer)
        if not pr_url or not pr_url.strip():
            self._logger.warning("Empty pr_url parameter", pr_url=pr_url)
            return False

        return True

    def sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize MCP tool parameters.

        Args:
            parameters: Raw parameters from MCP client

        Returns:
            Dict[str, Any]: Sanitized parameters
        """
        sanitized = {}

        for key, value in parameters.items():
            # Basic string sanitization
            if isinstance(value, str):
                sanitized[key] = value.strip()
            else:
                sanitized[key] = value

        return sanitized
