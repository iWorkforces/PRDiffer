"""Domain factory interfaces for Clean Architecture dependency injection."""

from .infrastructure_factory import InfrastructureFactoryInterface
from .application_factory import ApplicationFactoryInterface

__all__ = ['InfrastructureFactoryInterface', 'ApplicationFactoryInterface']
