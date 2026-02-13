"""Tests for ServiceFactory."""

import pytest
from unittest.mock import MagicMock, patch

from prdiffer.infrastructure.service_factory import (
    ServiceFactory,
    get_service_factory,
    reset_service_factory,
)
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.infrastructure.settings import SettingsService
from prdiffer.infrastructure.security.input_validator import InputValidator


@pytest.fixture(autouse=True)
def reset_factory():
    """Reset global factory before and after each test."""
    reset_service_factory()
    yield
    reset_service_factory()


class TestServiceFactory:
    """Tests for ServiceFactory class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        factory = ServiceFactory()

        assert factory._logger is not None
        assert factory._settings_service is not None
        assert factory._input_validator is not None

    def test_init_with_custom_logger(self):
        """Test initialization with custom logger."""
        custom_logger = MagicMock(spec=LoggerServiceInterface)
        factory = ServiceFactory(logger=custom_logger)

        assert factory._logger is custom_logger

    def test_init_with_custom_settings_service(self):
        """Test initialization with custom settings service."""
        custom_settings = MagicMock(spec=SettingsService)
        factory = ServiceFactory(settings_service=custom_settings)

        assert factory._settings_service is custom_settings

    def test_init_with_custom_input_validator(self):
        """Test initialization with custom input validator."""
        custom_validator = MagicMock(spec=InputValidator)
        factory = ServiceFactory(input_validator=custom_validator)

        assert factory._input_validator is custom_validator

    def test_init_with_all_custom(self):
        """Test initialization with all custom components."""
        custom_logger = MagicMock(spec=LoggerServiceInterface)
        custom_settings = MagicMock(spec=SettingsService)
        custom_validator = MagicMock(spec=InputValidator)

        factory = ServiceFactory(
            logger=custom_logger,
            settings_service=custom_settings,
            input_validator=custom_validator,
        )

        assert factory._logger is custom_logger
        assert factory._settings_service is custom_settings
        assert factory._input_validator is custom_validator

    def test_get_logger(self):
        """Test get_logger returns the logger."""
        custom_logger = MagicMock(spec=LoggerServiceInterface)
        factory = ServiceFactory(logger=custom_logger)

        result = factory.get_logger()

        assert result is custom_logger

    def test_get_logger_returns_default(self):
        """Test get_logger returns default logger when not specified."""
        factory = ServiceFactory()

        result = factory.get_logger()

        assert result is not None

    def test_get_settings_service(self):
        """Test get_settings_service returns the settings service."""
        custom_settings = MagicMock(spec=SettingsService)
        factory = ServiceFactory(settings_service=custom_settings)

        result = factory.get_settings_service()

        assert result is custom_settings

    def test_get_settings_service_returns_default(self):
        """Test get_settings_service returns default when not specified."""
        factory = ServiceFactory()

        result = factory.get_settings_service()

        assert result is not None

    def test_get_input_validator(self):
        """Test get_input_validator returns the validator."""
        custom_validator = MagicMock(spec=InputValidator)
        factory = ServiceFactory(input_validator=custom_validator)

        result = factory.get_input_validator()

        assert result is custom_validator

    def test_get_input_validator_returns_default(self):
        """Test get_input_validator returns default when not specified."""
        factory = ServiceFactory()

        result = factory.get_input_validator()

        assert result is not None


class TestGetServiceFactory:
    """Tests for get_service_factory function."""

    def test_creates_factory_on_first_call(self):
        """Test that factory is created on first call."""
        reset_service_factory()

        factory = get_service_factory()

        assert factory is not None
        assert isinstance(factory, ServiceFactory)

    def test_returns_same_instance_on_subsequent_calls(self):
        """Test that same instance is returned on subsequent calls."""
        reset_service_factory()

        factory1 = get_service_factory()
        factory2 = get_service_factory()

        assert factory1 is factory2

    def test_uses_custom_logger_on_first_call(self):
        """Test that custom logger is used on first call."""
        reset_service_factory()
        custom_logger = MagicMock(spec=LoggerServiceInterface)

        factory = get_service_factory(logger=custom_logger)

        assert factory.get_logger() is custom_logger

    def test_ignores_custom_logger_on_subsequent_calls(self):
        """Test that custom logger is ignored if factory already exists."""
        reset_service_factory()

        factory1 = get_service_factory()
        custom_logger = MagicMock(spec=LoggerServiceInterface)
        factory2 = get_service_factory(logger=custom_logger)

        assert factory1 is factory2
        assert factory2.get_logger() is not custom_logger

    def test_uses_custom_settings_on_first_call(self):
        """Test that custom settings is used on first call."""
        reset_service_factory()
        custom_settings = MagicMock(spec=SettingsService)

        factory = get_service_factory(settings_service=custom_settings)

        assert factory.get_settings_service() is custom_settings

    def test_uses_custom_validator_on_first_call(self):
        """Test that custom validator is used on first call."""
        reset_service_factory()
        custom_validator = MagicMock(spec=InputValidator)

        factory = get_service_factory(input_validator=custom_validator)

        assert factory.get_input_validator() is custom_validator


class TestResetServiceFactory:
    """Tests for reset_service_factory function."""

    def test_resets_global_factory(self):
        """Test that reset clears the global factory."""
        factory1 = get_service_factory()
        reset_service_factory()
        factory2 = get_service_factory()

        assert factory1 is not factory2

    def test_allows_reinitialization_with_different_components(self):
        """Test that after reset, factory can be reinitialized differently."""
        custom_logger1 = MagicMock(spec=LoggerServiceInterface)
        get_service_factory(logger=custom_logger1)

        reset_service_factory()

        custom_logger2 = MagicMock(spec=LoggerServiceInterface)
        factory = get_service_factory(logger=custom_logger2)

        assert factory.get_logger() is custom_logger2

    def test_multiple_resets(self):
        """Test that multiple resets work correctly."""
        factory1 = get_service_factory()
        reset_service_factory()
        reset_service_factory()
        factory2 = get_service_factory()

        assert factory1 is not factory2
