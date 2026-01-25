"""MCP tool plugin interface.

This interface defines the contract for MCP tools,
allowing modular tool development without modifying core server code.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class MCPToolPlugin(ABC):
    """Interface for MCP tool plugins.

    This abstraction enables:
        - Dynamic tool registration
        - Tool development without server modification
        - Multiple tools can coexist
        - Tool discovery and introspection

    Plugin Implementation Requirements:
        - Tool name and description
        - Parameter schema (JSON Schema compatible)
        - Async execute() method
        - Enabled/disabled state
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get tool name.

        Returns:
            str: Tool identifier (e.g., 'get_pr_diff', 'describe_pr')
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get tool description.

        Returns:
            str: Human-readable description
        """
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Get tool parameter schema.

        Returns:
            Dict[str, Any]: JSON Schema for parameters
            Format: https://json-schema.org/
        """
        pass

    @property
    def enabled(self) -> bool:
        """Check if tool is enabled.

        Returns:
            bool: True if tool should be active
        """
        return True

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            str: Tool execution result

        Raises:
            ValueError: If required parameters missing
            RuntimeError: If execution fails
        """
        pass

    @property
    def category(self) -> str:
        """Get tool category for organization.

        Returns:
            str: Category name (e.g., 'pr-operations', 'code-analysis')

        Defaults to 'general'
        """
        return "general"
