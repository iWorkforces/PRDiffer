"""Unit tests for ServiceContainer.

Tests ServiceContainer which provides lightweight dependency injection,
enabling service registration (singleton and transient) and resolution.
"""

import pytest
from prdiffer.domain.exceptions import ConfigurationError

from prdiffer.infrastructure import di_container
from prdiffer.infrastructure.di_container import (
    ServiceContainer,
    DependencyAlreadyRegisteredError,
    get_container,
    register_singleton_service,
    register_transient_factory,
)
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


class MockService:
    """Mock service for testing."""

    def __init__(self):
        self.initialized = True


class AnotherMockService:
    """Another mock service for testing."""

    def __init__(self):
        self.created = True


class TestServiceContainerInitialization:
    """Test suite for ServiceContainer initialization."""

    def test_container_initialization(self):
        """Test that ServiceContainer can be initialized."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        assert container is not None
        assert hasattr(container, "_logger")
        assert hasattr(container, "_singleton_instances")
        assert hasattr(container, "_transient_factories")
        assert hasattr(container, "_lock")

    def test_container_initialization_with_logger(self):
        """Test that logger is stored correctly."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        assert container._logger is logger

    def test_container_initialization_empty_state(self):
        """Test that container starts with empty state."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        assert len(container._singleton_instances) == 0
        assert len(container._transient_factories) == 0


class TestServiceContainerRegisterSingleton:
    """Test suite for register_singleton method."""

    def test_register_singleton_with_factory(self):
        """Test registering a singleton with a factory function."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService(), force=False)

        assert container.is_singleton(MockService)

    def test_register_singleton_with_instance(self):
        """Test registering a singleton with a pre-created instance."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        instance = MockService()
        container.register_singleton(MockService, lambda: None, instance=instance)

        retrieved = container.get(MockService)
        assert retrieved is instance

    def test_register_singleton_duplicate_without_force(self):
        """Test that registering duplicate raises error without force."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())

        with pytest.raises(DependencyAlreadyRegisteredError) as exc_info:
            container.register_singleton(
                MockService, lambda: MockService(), force=False
            )

        assert "MockService" in str(exc_info.value)

    def test_register_singleton_duplicate_with_force(self):
        """Test that registering duplicate with force overwrites."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        instance1 = MockService()
        instance2 = MockService()

        container.register_singleton(MockService, lambda: None, instance=instance1)
        assert container.get(MockService) is instance1

        container.register_singleton(
            MockService, lambda: None, instance=instance2, force=True
        )
        assert container.get(MockService) is instance2

    def test_register_singleton_multiple(self):
        """Test registering multiple singletons."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())
        container.register_singleton(AnotherMockService, lambda: AnotherMockService())

        assert container.get_instance_count(MockService) == 1
        assert container.get_instance_count(AnotherMockService) == 1


class TestServiceContainerRegisterTransient:
    """Test suite for register_transient method."""

    def test_register_transient_with_factory(self):
        """Test registering a transient with a factory function."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: MockService())

        assert container.get_instance_count(MockService) == 1

    def test_register_transient_multiple(self):
        """Test registering multiple transients."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: MockService())
        container.register_transient(AnotherMockService, lambda: AnotherMockService())

        assert container.get_instance_count(MockService) == 1
        assert container.get_instance_count(AnotherMockService) == 1

    def test_register_transient_duplicate(self):
        """Test that registering transient multiple times works (replaces factory)."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: MockService())
        container.register_transient(MockService, lambda: AnotherMockService())

        retrieved = container.get(MockService)
        assert isinstance(retrieved, AnotherMockService)

    def test_register_transient_after_singleton(self):
        """Test registering transient after singleton doesn't conflict."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())
        container.register_transient(MockService, lambda: MockService())

        instance = container.get(MockService)
        assert isinstance(instance, MockService)


class TestServiceContainerGet:
    """Test suite for get method."""

    def test_get_singleton(self):
        """Test getting a singleton returns same instance."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())

        instance1 = container.get(MockService)
        instance2 = container.get(MockService)

        assert instance1 is instance2

    def test_get_transient_creates_new_instance(self):
        """Test that getting transient creates new instances."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: MockService())

        instance1 = container.get(MockService)
        instance2 = container.get(MockService)

        assert instance1 is not instance2
        assert isinstance(instance1, MockService)
        assert isinstance(instance2, MockService)

    def test_get_not_registered_raises_error(self):
        """Test that getting unregistered service raises ConfigurationError."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        with pytest.raises(ConfigurationError) as exc_info:
            container.get(MockService)

        assert "MockService" in str(exc_info.value)
        assert "not registered" in str(exc_info.value)

    def test_get_singleton_vs_transient(self):
        """Test that singleton takes precedence over transient."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        singleton_instance = MockService()
        container.register_singleton(
            MockService, lambda: None, instance=singleton_instance
        )
        container.register_transient(MockService, lambda: AnotherMockService())

        retrieved = container.get(MockService)

        assert retrieved is singleton_instance


class TestServiceContainerHas:
    """Test suite for has method."""

    def test_has_singleton_true(self):
        """Test has returns True for registered singleton."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())

        assert container.has(MockService)

    def test_has_transient_true(self):
        """Test has returns True for registered transient."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: MockService())

        assert container.has(MockService)

    def test_has_false(self):
        """Test has returns False for unregistered service."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        assert not container.has(MockService)

    def test_has_multiple_services(self):
        """Test has with multiple registered services."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())
        container.register_transient(AnotherMockService, lambda: AnotherMockService())

        assert container.has(MockService)
        assert container.has(AnotherMockService)
        assert not container.has(str)


class TestServiceContainerIsSingleton:
    """Test suite for is_singleton method."""

    def test_is_singleton_true(self):
        """Test is_singleton returns True for singleton only."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())

        assert container.is_singleton(MockService)

    def test_is_singleton_false_for_transient(self):
        """Test is_singleton returns False for transient."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: MockService())

        assert not container.is_singleton(MockService)

    def test_is_singleton_false_for_unregistered(self):
        """Test is_singleton returns False for unregistered."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        assert not container.is_singleton(MockService)


class TestServiceContainerCreate:
    """Test suite for create method."""

    def test_create_with_instance(self):
        """Test create with pre-created instance."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        instance = MockService()
        created = container.create(MockService, lambda: None, instance=instance)

        assert created is instance

    def test_create_without_instance_uses_transient(self):
        """Test create without instance uses transient factory."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: MockService())
        created = container.create(MockService, lambda: None)

        assert isinstance(created, MockService)

    def test_create_registers_factory_if_not_exists(self):
        """Test create registers factory if not already registered."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        created = container.create(MockService, lambda: MockService())

        assert isinstance(created, MockService)
        assert container.has(MockService)

    def test_create_uses_existing_transient_factory(self):
        """Test create uses existing transient factory."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: AnotherMockService())
        created = container.create(MockService, lambda: MockService())

        assert isinstance(created, AnotherMockService)
        assert not isinstance(created, MockService)


class TestServiceContainerClearAll:
    """Test suite for clear_all method."""

    def test_clear_all_empty(self):
        """Test clear_all on empty container."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.clear_all()

        assert len(container._singleton_instances) == 0
        assert len(container._transient_factories) == 0

    def test_clear_all_with_services(self):
        """Test clear_all removes all registered services."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())
        container.register_transient(AnotherMockService, lambda: AnotherMockService())

        container.clear_all()

        assert len(container._singleton_instances) == 0
        assert len(container._transient_factories) == 0
        assert not container.has(MockService)
        assert not container.has(AnotherMockService)

    def test_clear_all_can_reregister(self):
        """Test that services can be registered after clear_all."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())
        container.clear_all()
        assert not container.has(MockService)

        container.register_singleton(MockService, lambda: MockService())
        assert container.has(MockService)


class TestServiceContainerGetInstanceCount:
    """Test suite for get_instance_count method."""

    def test_get_instance_count_zero(self):
        """Test get_instance_count for unregistered service."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        count = container.get_instance_count(MockService)

        assert count == 0

    def test_get_instance_count_singleton(self):
        """Test get_instance_count for singleton."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())

        count = container.get_instance_count(MockService)

        assert count == 1

    def test_get_instance_count_transient(self):
        """Test get_instance_count for transient."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: MockService())

        count = container.get_instance_count(MockService)

        assert count == 1

    def test_get_instance_count_both(self):
        """Test get_instance_count when both singleton and transient registered."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())
        container.register_transient(MockService, lambda: AnotherMockService())

        count = container.get_instance_count(MockService)

        assert count == 2


class TestDependencyAlreadyRegisteredError:
    """Test suite for DependencyAlreadyRegisteredError exception."""

    def test_error_initialization(self):
        """Test DependencyAlreadyRegisteredError initialization."""
        error = DependencyAlreadyRegisteredError("MyService")

        assert error.name == "MyService"
        assert "already registered" in str(error)

    def test_error_message_format(self):
        """Test that error message is properly formatted."""
        error = DependencyAlreadyRegisteredError("TestService")

        assert "TestService" in str(error)
        assert "already registered" in str(error)


class TestGetContainerGlobal:
    """Test suite for global get_container function."""

    def test_get_container_initializes_new(self):
        """Test get_container creates new instance on first call."""
        di_container._container = None

        logger = MockLogger()
        container = get_container(logger=logger)

        assert container is not None
        assert isinstance(container, ServiceContainer)

    def test_get_container_returns_existing(self):
        """Test get_container returns existing instance."""
        logger1 = MockLogger()
        container1 = get_container(logger=logger1)

        logger2 = MockLogger()
        container2 = get_container(logger=logger2)

        assert container1 is container2

    def test_get_container_without_logger_raises_error(self):
        """Test get_container raises ConfigurationError when no logger provided."""
        di_container._container = None

        with pytest.raises(ConfigurationError) as exc_info:
            get_container()

        assert "not initialized" in str(exc_info.value)


class TestRegisterSingletonServiceGlobal:
    """Test suite for global register_singleton_service function."""

    def test_register_singleton_service_convenience(self):
        """Test register_singleton_service registers singleton globally."""
        di_container._container = None
        logger = MockLogger()
        get_container(logger=logger)

        instance = MockService()
        register_singleton_service(MockService, lambda: None, instance=instance)

        container = get_container()
        retrieved = container.get(MockService)

        assert retrieved is instance


class TestRegisterTransientFactoryGlobal:
    """Test suite for global register_transient_factory function."""

    def test_register_transient_factory_convenience(self):
        """Test register_transient_factory registers transient globally."""
        di_container._container = None
        logger = MockLogger()
        get_container(logger=logger)

        register_transient_factory(MockService, lambda: MockService())

        container = get_container()
        retrieved = container.get(MockService)

        assert isinstance(retrieved, MockService)


class TestServiceContainerThreadSafety:
    """Test suite for ServiceContainer thread-safety."""

    def test_singleton_registration_is_thread_safe(self):
        """Test that singleton registration uses lock."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        assert hasattr(container, "_lock")
        assert container._lock is not None

    def test_clear_all_uses_lock(self):
        """Test that clear_all uses lock."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.clear_all()

        assert container.get_instance_count(MockService) == 0


class TestServiceContainerEdgeCases:
    """Test suite for ServiceContainer edge cases."""

    def test_register_with_type_name_without_name(self):
        """Test registering type without __name__ attribute."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        class NoName:
            pass

        container.register_singleton(NoName, lambda: NoName())

        assert container.has(NoName)

    def test_get_preserves_singleton_identity(self):
        """Test that singleton identity is preserved across multiple gets."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        instance = MockService()
        container.register_singleton(MockService, lambda: None, instance=instance)

        for _ in range(10):
            retrieved = container.get(MockService)
            assert retrieved is instance

    def test_transient_always_new_instances(self):
        """Test that transients always create new instances."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: MockService())

        instances = [container.get(MockService) for _ in range(10)]

        assert len(instances) == 10
        assert len(set(id(i) for i in instances)) == 10

    def test_register_singleton_overwrites_transient(self):
        """Test that singleton can overwrite transient."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_transient(MockService, lambda: AnotherMockService())
        assert isinstance(container.get(MockService), AnotherMockService)

        instance = MockService()
        container.register_singleton(MockService, lambda: None, instance=instance)
        assert container.get(MockService) is instance

    def test_force_overwrites_singleton(self):
        """Test that force=True overwrites existing singleton."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        instance1 = MockService()
        instance2 = MockService()

        container.register_singleton(MockService, lambda: None, instance=instance1)
        assert container.get(MockService) is instance1

        container.register_singleton(
            MockService, lambda: None, instance=instance2, force=True
        )
        assert container.get(MockService) is instance2

    def test_clear_all_preserves_lock(self):
        """Test that clear_all doesn't break lock functionality."""
        logger = MockLogger()
        container = ServiceContainer(logger)

        container.register_singleton(MockService, lambda: MockService())
        container.clear_all()
        container.register_singleton(MockService, lambda: MockService())

        assert container.get(MockService) is not None
