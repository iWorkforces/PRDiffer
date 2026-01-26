"""Service factory for creating service instances.

This module provides factory functions for creating commonly used services,
facilitating dependency injection and testability.
"""

from typing import Optional
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.infrastructure.settings import SettingsService
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.security.input_validator import InputValidator


class ServiceFactory:
    """Factory for creating service instances with dependency injection.

    This factory provides:
        - Centralized service creation
        - Support for dependency injection
        - Default fallback implementations
        - Type-safe service instantiation
    """

    def __init__(
        self,
        logger: Optional[LoggerServiceInterface] = None,
        settings_service: Optional[SettingsService] = None,
        input_validator: Optional[InputValidator] = None,
    ):
        """Initialize service factory.

        Args:
            logger: Optional logger service (defaults to get_logger())
            settings_service: Optional settings service (defaults to new instance)
            input_validator: Optional input validator (defaults to new instance)
        """
        self._logger = logger or get_logger()
        self._settings_service = settings_service or SettingsService()
        self._input_validator = input_validator or InputValidator()

    def get_logger(self) -> LoggerServiceInterface:
        """Get logger service instance.

        Returns:
            LoggerServiceInterface: Logger service
        """
        return self._logger

    def get_settings_service(self) -> SettingsService:
        """Get settings service instance.

        Returns:
            SettingsService: Settings service
        """
        return self._settings_service

    def get_input_validator(self) -> InputValidator:
        """Get input validator instance.

        Returns:
            InputValidator: Input validator
        """
        return self._input_validator


# Global service factory instance
_service_factory: Optional[ServiceFactory] = None


def get_service_factory(
    logger: Optional[LoggerServiceInterface] = None,
    settings_service: Optional[SettingsService] = None,
    input_validator: Optional[InputValidator] = None,
) -> ServiceFactory:
    """Get or create global service factory.

    Args:
        logger: Optional logger for first-time initialization
        settings_service: Optional settings for first-time initialization
        input_validator: Optional validator for first-time initialization

    Returns:
        ServiceFactory: Global service factory instance
    """
    global _service_factory

    if _service_factory is None:
        _service_factory = ServiceFactory(
            logger=logger,
            settings_service=settings_service,
            input_validator=input_validator,
        )

    return _service_factory


def reset_service_factory() -> None:
    """Reset global service factory.

    Useful for testing or container cleanup.
    """
    global _service_factory
    _service_factory = None
