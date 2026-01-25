"""Plugin manager for MCP tools.

This module provides centralized management for MCP tool plugins,
enabling dynamic tool registration, discovery, and execution.
"""

from typing import Dict, Optional, List
from prdiffer.application.interfaces.tool_plugin import MCPToolPlugin
from prdiffer.domain.services.logger import LoggerServiceInterface


class PluginManager:
    """Manages MCP tool plugins.

    Enables:
        - Dynamic tool registration at runtime
        - Tool discovery by name or category
        - Enabled/disabled state management
        - Tool execution with proper error handling
    """

    def __init__(self, logger: LoggerServiceInterface):
        """Initialize plugin manager.

        Args:
            logger: Logger service instance
        """
        self._plugins: Dict[str, MCPToolPlugin] = {}
        self._logger = logger

    def register_plugin(self, plugin: MCPToolPlugin) -> None:
        """Register an MCP tool plugin.

        Args:
            plugin: Plugin instance implementing MCPToolPlugin

        Raises:
            ValueError: If plugin name already exists
            TypeError: If plugin doesn't implement MCPToolPlugin
        """
        if not isinstance(plugin, MCPToolPlugin):
            raise TypeError(f"Plugin {plugin.name} must implement MCPToolPlugin")

        if plugin.name in self._plugins:
            raise ValueError(f"Plugin {plugin.name} already registered")

        self._plugins[plugin.name] = plugin
        self._logger.info(f"Registered plugin: {plugin.name}")

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister an MCP tool plugin.

        Args:
            plugin_name: Name of plugin to unregister
        """
        if plugin_name not in self._plugins:
            self._logger.warning(f"Plugin {plugin_name} not found, cannot unregister")
            return

        del self._plugins[plugin_name]
        self._logger.info(f"Unregistered plugin: {plugin_name}")

    def get_plugin(self, tool_name: str) -> Optional[MCPToolPlugin]:
        """Get plugin by name.

        Args:
            tool_name: Tool name

        Returns:
            MCPToolPlugin: Plugin instance or None if not found
        """
        return self._plugins.get(tool_name)

    def get_plugin_by_name(self, tool_name: str) -> Optional[MCPToolPlugin]:
        """Get plugin by name (alias for get_plugin).

        Args:
            tool_name: Tool name

        Returns:
            MCPToolPlugin: Plugin instance or None if not found
        """
        return self.get_plugin(tool_name)

    def list_plugins(self, enabled_only: bool = True) -> List[str]:
        """List all registered plugins.

        Args:
            enabled_only: If True, only return enabled plugins

        Returns:
            List[str]: List of plugin names
        """
        plugins = self._plugins

        if enabled_only:
            enabled_plugins = {}
            for name, plugin in self._plugins.items():
                if plugin.enabled:
                    enabled_plugins[name] = plugin
            plugins = enabled_plugins

        return list(plugins.keys())

    async def execute_plugin(self, tool_name: str, **kwargs) -> str:
        """Execute a plugin by name.

        Args:
            tool_name: Tool name
            **kwargs: Plugin parameters

        Returns:
            str: Plugin execution result
        """
        plugin = self.get_plugin(tool_name)

        if not plugin:
            raise ValueError(f"Plugin {tool_name} not found")

        if not plugin.enabled:
            raise RuntimeError(f"Plugin {tool_name} is disabled")

        return await plugin.execute(**kwargs)

    def list_plugin_names(self) -> List[str]:
        """List all plugin names.

        Returns:
            List[str]: List of plugin names
        """
        return self.list_plugins(enabled_only=False)

    def get_plugin_count(self) -> int:
        """Get count of registered plugins.

        Returns:
            int: Number of registered plugins
        """
        return len(self._plugins)

    def clear_all(self) -> None:
        """Clear all registered plugins.

        Useful for testing or resetting state.
        """
        self._plugins.clear()
        self._logger.info("Cleared all plugins")
