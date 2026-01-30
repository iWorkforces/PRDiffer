"""Dependency injection container for PRDifferMCP.

This module provides a lightweight DI container for managing service lifecycles,
enabling testability and proper dependency injection throughout the codebase.
"""

from typing import Dict, Type, Callable, Any, Optional
from threading import Lock
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.exceptions import PRDifferException, ConfigurationError
from prdiffer.domain.errors import E5009_CONFIGURATION_ERROR


class DependencyAlreadyRegisteredError(PRDifferException):
    """Raised when attempting to register a dependency that's already registered."""

    def __init__(self, name: str):
        self.name = name
        message = f"Dependency '{name}' is already registered"
        super().__init__(message=message)


class ServiceContainer:
    """Lightweight dependency injection container.

    Provides:
        - Service registration (singleton and transient)
        - Service resolution by interface type
        - Lifecycle management (singletons vs transients)
        - Thread-safe operations
        - Clear error handling

    Design Goals:
        - Simple API: get(), create()
        - Type-safe with full type hints
        - Thread-safe: Locks for concurrent safety
        - No external dependencies beyond domain interfaces
        - Fast: minimal overhead
    """

    _singleton_instances: dict[str, Any] = {}
    _transient_factories: dict[str, Callable] = {}
    _lock: Lock
    _logger: LoggerServiceInterface

    def __init__(self, logger: LoggerServiceInterface):
        """Initialize service container.

        Args:
            logger: Logger service instance
        """
        self._lock = Lock()
        self._logger = logger
        self._singleton_instances: dict[str, Any] = {}
        self._transient_factories: dict[str, Callable] = {}

    def register_singleton(
        self,
        interface_type: Type,
        factory: Callable,
        force: bool = False,
        instance: Optional[Any] = None,
    ) -> None:
        """Register a singleton service.

        Args:
            interface_type: Interface type (e.g., LoggerServiceInterface)
            factory: Factory function that creates instance
            force: Force re-registration even if exists
            instance: Optional pre-created instance (for testing)

        Raises:
            DependencyAlreadyRegisteredError: If interface_type already registered with force=False

        Usage:
            Container tracks singletons that should persist for application lifetime
            Singletons should be created once and reused
        """
        type_name = (
            interface_type.__name__
            if hasattr(interface_type, "__name__")
            else interface_type.__class__.__name__
        )

        with self._lock:
            if type_name in self._singleton_instances and not force:
                raise DependencyAlreadyRegisteredError(type_name)

        if instance is not None:
            self._singleton_instances[type_name] = instance
        else:
            self._singleton_instances[type_name] = factory()

        self._logger.debug(f"Registered singleton: {type_name}")

    def register_transient(
        self,
        interface_type: Type,
        factory: Callable,
    ) -> None:
        """Register a transient service.

        Args:
            interface_type: Interface type (e.g., CacheServiceInterface)
            factory: Factory function that creates instances

        Usage:
            Container creates new instance on each get() call
            Transients don't persist between calls
            Ideal for stateless services or caches
        """
        type_name = (
            interface_type.__name__
            if hasattr(interface_type, "__name__")
            else interface_type.__class__.__name__
        )

        self._transient_factories[type_name] = factory
        self._logger.debug(f"Registered transient factory: {type_name}")

    def get(
        self,
        interface_type: Type,
    ) -> Any:
        """Get service instance by interface type.

        Args:
            interface_type: Interface type (e.g., LoggerServiceInterface)

        Returns:
            Any: Service instance

        Raises:
            ValueError: If interface_type not registered
        """
        type_name = (
            interface_type.__name__
            if hasattr(interface_type, "__name__")
            else interface_type.__class__.__name__
        )

        if type_name in self._singleton_instances:
            return self._singleton_instances[type_name]

        if type_name in self._transient_factories:
            factory = self._transient_factories[type_name]
            instance = factory()
            self._logger.debug(f"Created transient instance of {type_name}")
            return instance

        raise ConfigurationError(
            f"Service {type_name} not registered", error_code=E5009_CONFIGURATION_ERROR
        )

    def has(self, interface_type: Type) -> bool:
        """Check if interface type is registered.

        Args:
            interface_type: Interface type (e.g., LoggerServiceInterface)

        Returns:
            bool: True if registered as singleton or transient
        """
        type_name = (
            interface_type.__name__
            if hasattr(interface_type, "__name__")
            else interface_type.__class__.__name__
        )

        return (
            type_name in self._singleton_instances
            or type_name in self._transient_factories
        )

    def is_singleton(self, interface_type: Type) -> bool:
        """Check if interface type is registered as singleton.

        Args:
            interface_type: Interface type (e.g., LoggerServiceInterface)

        Returns:
            bool: True if registered as singleton only
        """
        type_name = (
            interface_type.__name__
            if hasattr(interface_type, "__name__")
            else interface_type.__class__.__name__
        )

        return (
            type_name in self._singleton_instances
            and type_name not in self._transient_factories
        )

    def create(
        self,
        interface_type: Type,
        factory: Callable,
        instance: Optional[Any] = None,
    ) -> Any:
        """Create and register a service instance.

        Args:
            interface_type: Interface type (e.g., LoggerServiceInterface)
            factory: Factory function that creates instance
            instance: Optional pre-created instance (for testing)

        Returns:
            Any: Service instance

        Usage:
            Similar to get() but allows specifying instance
        """
        type_name = (
            interface_type.__name__
            if hasattr(interface_type, "__name__")
            else interface_type.__class__.__name__
        )

        if instance is not None:
            self._singleton_instances[type_name] = instance
            self._logger.debug(f"Created singleton instance of {type_name}")
            return instance

        if type_name in self._transient_factories:
            factory = self._transient_factories[type_name]
        else:
            self._transient_factories[type_name] = factory

        instance = factory()
        self._logger.debug(f"Created transient instance of {type_name}")

        return instance

    def clear_all(self) -> None:
        """Clear all registered services.

        Useful for testing or resetting state.

        Usage:
            Testing: Reset container state between tests
            Restarting: Clear memory leaks
        """
        with self._lock:
            self._singleton_instances.clear()
            self._transient_factories.clear()
            self._logger.info("Cleared all services")

    def get_instance_count(self, interface_type: Type) -> int:
        """Get count of registered instances (singleton + transient).

        Args:
            interface_type: Interface type (e.g., LoggerServiceInterface)

        Returns:
            int: Total registered instances (1 if singleton, 1 if transient, 0 if not registered)
        """
        type_name = (
            interface_type.__name__
            if hasattr(interface_type, "__name__")
            else interface_type.__class__.__name__
        )

        count = 0
        if type_name in self._singleton_instances:
            count += 1
        if type_name in self._transient_factories:
            count += 1

        return count


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container(logger: Optional[LoggerServiceInterface] = None) -> ServiceContainer:
    """Get or create global service container.

    Args:
        logger: Optional logger service for first-time initialization

    Returns:
        ServiceContainer: Global container instance

    Raises:
        ValueError: If container not initialized and no logger provided
    """
    global _container

    if _container is None:
        if logger is None:
            raise ConfigurationError(
                "ServiceContainer not initialized. Provide logger on first call.",
                error_code=E5009_CONFIGURATION_ERROR,
            )
        _container = ServiceContainer(logger=logger)

    return _container


def register_singleton_service(
    interface_type: Type, factory: Callable, instance: Optional[Any] = None
) -> None:
    """Convenience function to register a singleton service.

    Args:
        interface_type: Interface type (e.g., LoggerServiceInterface)
        factory: Factory function that creates instance
        instance: Optional pre-created instance (for testing)
    """
    container = get_container()
    container.register_singleton(interface_type, factory, instance=instance)


def register_transient_factory(interface_type: Type, factory: Callable) -> None:
    """Convenience function to register a transient factory.

    Args:
        interface_type: Interface type (e.g., CacheServiceInterface)
        factory: Factory function that creates instances

    Usage:
            For services that don't need to persist
    """
    container = get_container()
    container.register_transient(interface_type, factory)
