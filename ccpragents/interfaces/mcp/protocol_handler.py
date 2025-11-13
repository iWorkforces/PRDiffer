"""MCP protocol handler for Clean Architecture.

This component handles MCP protocol-specific operations while delegating
business logic to the application layer.
"""

from typing import Any, Dict, Optional
from abc import ABC, abstractmethod

from ccpragents.domain.services.logger import LoggerServiceInterface


class MCPProtocolHandlerInterface(ABC):
    """Abstract interface for MCP protocol handling."""

    @abstractmethod
    async def handle_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Handle an MCP tool call.

        Args:
            tool_name: Name of the tool being called
            parameters: Parameters passed to the tool

        Returns:
            Result of the tool execution
        """
        pass

    @abstractmethod
    def register_tool(self, tool_name: str, tool_function: callable, description: str) -> None:
        """Register an MCP tool.

        Args:
            tool_name: Name of the tool
            tool_function: Function to execute when tool is called
            description: Description of the tool
        """
        pass

    @abstractmethod
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information for MCP protocol.

        Returns:
            Dictionary containing server information
        """
        pass


class MCPProtocolHandler(MCPProtocolHandlerInterface):
    """Concrete MCP protocol handler implementation."""

    def __init__(self, logger: LoggerServiceInterface):
        """Initialize MCP protocol handler.

        Args:
            logger: Logger service for structured logging
        """
        self._logger = logger
        self._tools: Dict[str, callable] = {}
        self._tool_descriptions: Dict[str, str] = {}

    async def handle_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Handle an MCP tool call.

        Args:
            tool_name: Name of the tool being called
            parameters: Parameters passed to the tool

        Returns:
            Result of the tool execution

        Raises:
            ValueError: If tool is not registered
        """
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' is not registered")

        tool_function = self._tools[tool_name]
        self._logger.info(
            "Executing MCP tool",
            tool_name=tool_name,
            parameters=parameters
        )

        try:
            result = await tool_function(**parameters)
            self._logger.info(
                "MCP tool execution completed",
                tool_name=tool_name,
                success=True
            )
            return result
        except Exception as e:
            self._logger.error(
                "MCP tool execution failed",
                tool_name=tool_name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def register_tool(self, tool_name: str, tool_function: callable, description: str) -> None:
        """Register an MCP tool.

        Args:
            tool_name: Name of the tool
            tool_function: Function to execute when tool is called
            description: Description of the tool
        """
        self._tools[tool_name] = tool_function
        self._tool_descriptions[tool_name] = description

        self._logger.info(
            "Registered MCP tool",
            tool_name=tool_name,
            description=description
        )

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information for MCP protocol.

        Returns:
            Dictionary containing server information
        """
        return {
            "name": "ccpragents",
            "version": "0.1.3",
            "tools": list(self._tool_descriptions.keys()),
            "tool_descriptions": self._tool_descriptions
        }