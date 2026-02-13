"""Unit tests for PluginManager.

Tests PluginManager which manages MCP tool plugins,
enabling dynamic tool registration, discovery, and execution.
"""

import pytest

from prdiffer.application.plugin_manager import PluginManager
from prdiffer.domain.exceptions import ValidationError, PRDifferException
from prdiffer.application.interfaces.tool_plugin import MCPToolPlugin
from prdiffer.domain.services.logger import LoggerServiceInterface


class MockLogger(LoggerServiceInterface):
    """Mock logger for testing."""

    def debug(self, message: str, **kwargs) -> None:
        pass

    def info(self, message: str, **kwargs) -> None:
        pass

    def warning(self, message: str, **kwargs) -> None:
        pass

    def error(self, message: str, **kwargs) -> None:
        pass

    def critical(self, message: str, **kwargs) -> None:
        pass

    def should_log(self, level) -> bool:
        return True


class MockPlugin(MCPToolPlugin):
    """Mock plugin for testing."""

    @property
    def name(self) -> str:
        return "mock_plugin"

    @property
    def description(self) -> str:
        return "Mock plugin for testing"

    @property
    def parameters(self) -> dict:
        return {"type": "object"}

    @property
    def enabled(self) -> bool:
        return True

    async def execute(self, **kwargs) -> str:
        return "mock result"


class AnotherMockPlugin(MCPToolPlugin):
    """Another mock plugin for testing."""

    @property
    def name(self) -> str:
        return "another_plugin"

    @property
    def description(self) -> str:
        return "Another mock plugin"

    @property
    def parameters(self) -> dict:
        return {"type": "string"}

    @property
    def enabled(self) -> bool:
        return True

    async def execute(self, **kwargs) -> str:
        return "another result"


class DisabledMockPlugin(MCPToolPlugin):
    """Mock plugin that is disabled."""

    @property
    def name(self) -> str:
        return "disabled_plugin"

    @property
    def description(self) -> str:
        return "Disabled plugin"

    @property
    def parameters(self) -> dict:
        return {"type": "boolean"}

    @property
    def enabled(self) -> bool:
        return False

    async def execute(self, **kwargs) -> str:
        return "disabled result"


class TestPluginManagerInitialization:
    """Test suite for PluginManager initialization."""

    def test_plugin_manager_initialization(self):
        """Test that PluginManager can be initialized."""
        logger = MockLogger()
        manager = PluginManager(logger)

        assert manager is not None
        assert hasattr(manager, "_plugins")
        assert hasattr(manager, "_logger")

    def test_plugin_manager_initialization_with_logger(self):
        """Test that logger is stored correctly."""
        logger = MockLogger()
        manager = PluginManager(logger)

        assert manager._logger is logger

    def test_plugin_manager_initialization_empty(self):
        """Test that manager starts with empty plugins."""
        logger = MockLogger()
        manager = PluginManager(logger)

        assert len(manager._plugins) == 0
        assert manager.get_plugin_count() == 0


class TestPluginManagerRegisterPlugin:
    """Test suite for register_plugin method."""

    def test_register_plugin_valid(self):
        """Test registering a valid plugin."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()

        manager.register_plugin(plugin)

        assert manager.get_plugin_count() == 1
        assert plugin.name in manager.list_plugins()

    def test_register_plugin_multiple(self):
        """Test registering multiple plugins."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = AnotherMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)

        assert manager.get_plugin_count() == 2
        assert plugin1.name in manager.list_plugins()
        assert plugin2.name in manager.list_plugins()

    def test_register_plugin_duplicate_raises_error(self):
        """Test that registering duplicate plugin raises ValueError."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = MockPlugin()

        manager.register_plugin(plugin1)

        with pytest.raises(ValidationError) as exc_info:
            manager.register_plugin(plugin2)

        assert "already registered" in str(exc_info.value)
        assert plugin1.name in str(exc_info.value)

    def test_unregister_existing_plugin(self):
        """Test unregistering an existing plugin."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()

        manager.register_plugin(plugin)
        assert manager.get_plugin_count() == 1

        manager.unregister_plugin(plugin.name)

        assert manager.get_plugin_count() == 0
        assert plugin.name not in manager.list_plugins()

    def test_unregister_nonexistent_plugin(self):
        """Test unregistering non-existent plugin logs warning."""
        logger = MockLogger()
        manager = PluginManager(logger)

        manager.unregister_plugin("nonexistent")

        assert manager.get_plugin_count() == 0

    def test_unregister_from_multiple(self):
        """Test unregistering one plugin from multiple."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = AnotherMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)
        assert manager.get_plugin_count() == 2

        manager.unregister_plugin(plugin1.name)

        assert manager.get_plugin_count() == 1
        assert plugin1.name not in manager.list_plugins()
        assert plugin2.name in manager.list_plugins()


class TestPluginManagerGetPlugin:
    """Test suite for get_plugin method."""

    def test_get_plugin_existing(self):
        """Test getting an existing plugin."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()

        manager.register_plugin(plugin)
        retrieved = manager.get_plugin(plugin.name)

        assert retrieved is plugin

    def test_get_plugin_nonexistent(self):
        """Test getting non-existent plugin returns None."""
        logger = MockLogger()
        manager = PluginManager(logger)

        retrieved = manager.get_plugin("nonexistent")

        assert retrieved is None

    def test_get_plugin_from_multiple(self):
        """Test getting specific plugin from multiple registered."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = AnotherMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)

        retrieved = manager.get_plugin(plugin2.name)

        assert retrieved is plugin2


class TestPluginManagerGetPluginByName:
    """Test suite for get_plugin_by_name method."""

    def test_get_plugin_by_name_existing(self):
        """Test getting plugin by name when it exists."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()

        manager.register_plugin(plugin)
        retrieved = manager.get_plugin_by_name(plugin.name)

        assert retrieved is plugin

    def test_get_plugin_by_name_nonexistent(self):
        """Test getting plugin by name when it doesn't exist."""
        logger = MockLogger()
        manager = PluginManager(logger)

        retrieved = manager.get_plugin_by_name("nonexistent")

        assert retrieved is None

    def test_get_plugin_by_name_is_alias(self):
        """Test that get_plugin_by_name is alias for get_plugin."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()

        manager.register_plugin(plugin)

        result1 = manager.get_plugin(plugin.name)
        result2 = manager.get_plugin_by_name(plugin.name)

        assert result1 is result2


class TestPluginManagerListPlugins:
    """Test suite for list_plugins method."""

    def test_list_plugins_empty(self):
        """Test listing plugins when none are registered."""
        logger = MockLogger()
        manager = PluginManager(logger)

        plugins = manager.list_plugins()

        assert isinstance(plugins, list)
        assert len(plugins) == 0

    def test_list_plugins_enabled_only(self):
        """Test listing only enabled plugins."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = DisabledMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)

        enabled_plugins = manager.list_plugins(enabled_only=True)

        assert plugin1.name in enabled_plugins
        assert plugin2.name not in enabled_plugins
        assert len(enabled_plugins) == 1

    def test_list_plugins_all(self):
        """Test listing all plugins including disabled."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = DisabledMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)

        all_plugins = manager.list_plugins(enabled_only=False)

        assert plugin1.name in all_plugins
        assert plugin2.name in all_plugins
        assert len(all_plugins) == 2

    def test_list_plugins_default_enabled_only(self):
        """Test that list_plugins defaults to enabled_only=True."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = DisabledMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)

        plugins = manager.list_plugins()

        assert plugin1.name in plugins
        assert plugin2.name not in plugins


class TestPluginManagerExecutePlugin:
    """Test suite for execute_plugin method."""

    @pytest.mark.asyncio
    async def test_execute_plugin_enabled(self):
        """Test executing an enabled plugin."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()

        manager.register_plugin(plugin)

        result = await manager.execute_plugin(plugin.name, param="value")

        assert result == "mock result"

    @pytest.mark.asyncio
    async def test_execute_plugin_disabled_raises_error(self):
        """Test that executing disabled plugin raises RuntimeError."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = DisabledMockPlugin()

        manager.register_plugin(plugin)

        with pytest.raises(PRDifferException) as exc_info:
            await manager.execute_plugin(plugin.name)

        assert "is disabled" in str(exc_info.value)
        assert plugin.name in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_plugin_nonexistent_raises_error(self):
        """Test that executing non-existent plugin raises ValueError."""
        logger = MockLogger()
        manager = PluginManager(logger)

        with pytest.raises(ValidationError) as exc_info:
            await manager.execute_plugin("nonexistent")

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_plugin_with_parameters(self):
        """Test executing plugin with parameters."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()

        manager.register_plugin(plugin)

        result = await manager.execute_plugin(plugin.name, arg1="value1", arg2="value2")

        assert result == "mock result"

    @pytest.mark.asyncio
    async def test_execute_plugin_with_kwargs(self):
        """Test executing plugin with **kwargs."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()

        manager.register_plugin(plugin)

        kwargs = {"param1": "value1", "param2": "value2"}
        result = await manager.execute_plugin(plugin.name, **kwargs)

        assert result == "mock result"


class TestPluginManagerListPluginNames:
    """Test suite for list_plugin_names method."""

    def test_list_plugin_names_empty(self):
        """Test listing plugin names when none are registered."""
        logger = MockLogger()
        manager = PluginManager(logger)

        names = manager.list_plugin_names()

        assert isinstance(names, list)
        assert len(names) == 0

    def test_list_plugin_names_with_plugins(self):
        """Test listing plugin names with registered plugins."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = AnotherMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)

        names = manager.list_plugin_names()

        assert plugin1.name in names
        assert plugin2.name in names
        assert len(names) == 2

    def test_list_plugin_names_includes_disabled(self):
        """Test that list_plugin_names includes disabled plugins."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = DisabledMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)

        names = manager.list_plugin_names()

        assert plugin1.name in names
        assert plugin2.name in names
        assert len(names) == 2


class TestPluginManagerGetPluginCount:
    """Test suite for get_plugin_count method."""

    def test_get_plugin_count_empty(self):
        """Test getting count when no plugins registered."""
        logger = MockLogger()
        manager = PluginManager(logger)

        count = manager.get_plugin_count()

        assert count == 0

    def test_get_plugin_count_single(self):
        """Test getting count with one plugin."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()

        manager.register_plugin(plugin)
        count = manager.get_plugin_count()

        assert count == 1

    def test_get_plugin_count_multiple(self):
        """Test getting count with multiple plugins."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = AnotherMockPlugin()
        plugin3 = DisabledMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)
        manager.register_plugin(plugin3)

        count = manager.get_plugin_count()

        assert count == 3

    def test_get_plugin_count_after_unregister(self):
        """Test count decreases after unregistering."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = AnotherMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)
        assert manager.get_plugin_count() == 2

        manager.unregister_plugin(plugin1.name)
        assert manager.get_plugin_count() == 1


class TestPluginManagerClearAll:
    """Test suite for clear_all method."""

    def test_clear_all_empty(self):
        """Test clearing when no plugins are registered."""
        logger = MockLogger()
        manager = PluginManager(logger)

        manager.clear_all()

        assert manager.get_plugin_count() == 0
        assert manager.list_plugins() == []

    def test_clear_all_with_plugins(self):
        """Test clearing all registered plugins."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = AnotherMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)
        assert manager.get_plugin_count() == 2

        manager.clear_all()

        assert manager.get_plugin_count() == 0
        assert manager.list_plugins() == []

    def test_clear_all_can_reregister(self):
        """Test that plugins can be registered after clear_all."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()

        manager.register_plugin(plugin)
        assert manager.get_plugin_count() == 1

        manager.clear_all()
        assert manager.get_plugin_count() == 0

        plugin2 = MockPlugin()
        manager.register_plugin(plugin2)
        assert manager.get_plugin_count() == 1


class TestPluginManagerEdgeCases:
    """Test suite for PluginManager edge cases."""

    def test_register_plugin_with_special_name(self):
        """Test registering plugin with special characters in name."""
        logger = MockLogger()
        manager = PluginManager(logger)

        class SpecialNamePlugin(MCPToolPlugin):
            @property
            def name(self) -> str:
                return "my-plugin_v2"

            @property
            def description(self) -> str:
                return "Special name plugin"

            @property
            def parameters(self) -> dict:
                return {"type": "object"}

            @property
            def enabled(self) -> bool:
                return True

            async def execute(self, **kwargs) -> str:
                return "special result"

        plugin = SpecialNamePlugin()
        manager.register_plugin(plugin)

        assert "my-plugin_v2" in manager.list_plugins()

    def test_get_plugin_case_sensitive(self):
        """Test that plugin name lookup is case-sensitive."""
        logger = MockLogger()
        manager = PluginManager(logger)

        class UppercasePlugin(MCPToolPlugin):
            @property
            def name(self) -> str:
                return "MY_PLUGIN"

            @property
            def description(self) -> str:
                return "Uppercase plugin"

            @property
            def parameters(self) -> dict:
                return {"type": "object"}

            @property
            def enabled(self) -> bool:
                return True

            async def execute(self, **kwargs) -> str:
                return "uppercase result"

        plugin = UppercasePlugin()
        manager.register_plugin(plugin)

        assert manager.get_plugin("MY_PLUGIN") is plugin
        assert manager.get_plugin("my_plugin") is None

    def test_enabled_disabled_affects_list_plugins(self):
        """Test that enabled property affects list_plugins with enabled_only=True."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = DisabledMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)

        enabled_list = manager.list_plugins(enabled_only=True)
        all_list = manager.list_plugins(enabled_only=False)

        assert len(enabled_list) == 1
        assert len(all_list) == 2
        assert plugin1.name in enabled_list
        assert plugin2.name not in enabled_list
        assert plugin2.name in all_list

    def test_unregister_and_reregister_same_name(self):
        """Test that plugin can be unregistered and re-registered."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin = MockPlugin()
        plugin2 = MockPlugin()

        manager.register_plugin(plugin)
        assert manager.get_plugin_count() == 1

        manager.unregister_plugin(plugin.name)
        assert manager.get_plugin_count() == 0

        manager.register_plugin(plugin2)
        assert manager.get_plugin_count() == 1

    @pytest.mark.asyncio
    async def test_execute_multiple_plugins(self):
        """Test executing multiple plugins in sequence."""
        logger = MockLogger()
        manager = PluginManager(logger)
        plugin1 = MockPlugin()
        plugin2 = AnotherMockPlugin()

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)

        result1 = await manager.execute_plugin(plugin1.name)
        result2 = await manager.execute_plugin(plugin2.name)

        assert result1 == "mock result"
        assert result2 == "another result"
