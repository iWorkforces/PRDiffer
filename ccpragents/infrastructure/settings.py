from typing import Optional, Dict, Any, cast, List
import logging
import os
from pathlib import Path
from dynaconf import Dynaconf
from dynaconf.validator import Validator, ValidationError
from ccpragents.domain.services import SettingsServiceInterface
from ccpragents.infrastructure.utils.cache_decorator import CachingMixin, cached_method


class SettingsService(SettingsServiceInterface, CachingMixin):
    """Settings service for reading TOML configuration files with Dynaconf and caching.

    This service provides a centralized way to access application settings with
    built-in caching for maximum performance using the CachingMixin decorator pattern.

    Attributes:
        settings: The Dynaconf instance for configuration management
    """

    def __init__(
        self,
        settings_files: Optional[list] = None,
        max_cache_size: int = 1000,
        cache_ttl: int = 300,
    ):
        """Initialize the settings service with configuration files.

        Args:
            settings_files: List of TOML files to load. Defaults to ['settings.toml', '.secrets.toml']
            max_cache_size: Maximum number of cache entries (default: 1000)
            cache_ttl: Default TTL for cached settings in seconds (default: 300 = 5 minutes)
        """
        # Initialize CachingMixin with configurable parameters
        super().__init__(max_cache_size=max_cache_size, default_ttl=cache_ttl)

        if settings_files is None:
            settings_files = ["settings.toml", ".secrets.toml"]

        self.settings = Dynaconf(
            settings_files=settings_files,
            environments=True,
            env_switcher="ENV_FOR_DYNACONF",
            load_dotenv=True,
        )

    @cached_method()
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with caching.

        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found

        Returns:
            Any: The configuration value or default
        """
        # Use cast to tell type checker that settings.get returns the expected type
        return cast(Any, self.settings.get(key, default))  # type: ignore[misc]

    @cached_method()
    def get_github_settings(self) -> Dict[str, Any]:
        """Get GitHub-related settings with caching.

        Note: GitHub token authentication is now exclusively managed via the
        GITHUB_TOKEN environment variable. It is no longer read from settings files.

        Returns:
            Dict[str, Any]: GitHub configuration including rate limits, timeouts, etc.
        """

        # Get settings from current environment, fall back to default environment if not found
        def get_with_fallback(key, default=None):
            value = self.get(key)
            if value is None and hasattr(self.settings, "from_env"):
                # Fall back to default environment
                default_settings = cast(Dynaconf, self.settings.from_env("default"))  # type: ignore[misc]
                value = cast(Any, default_settings.get(key, default))  # type: ignore[misc]
            return value or default

        return {
            "rate_limit": get_with_fallback("github.rate_limit", 5000),
            "timeout": get_with_fallback("github.timeout", 30),
            "max_retries": get_with_fallback("github.max_retries", 3),
            "retry_delay": get_with_fallback("github.retry_delay", 1),
            "ignore_patterns": tuple(get_with_fallback("github.ignore_patterns", [])),
            "valid_extensions": tuple(get_with_fallback("github.valid_extensions", [])),
        }

    @cached_method()
    def get_cache_settings(self) -> Dict[str, Any]:
        """Get cache-related settings with caching.

        Returns:
            Dict[str, Any]: Cache configuration including TTL and size limits
        """
        return {
            "ttl": self.get("cache.ttl", 300),  # 5 minutes default
            "max_size": self.get("cache.max_size", 1000),
            "enabled": self.get("cache.enabled", True),
        }

    @cached_method()
    def get_app_settings(self) -> Dict[str, Any]:
        """Get general application settings with caching.

        Returns:
            Dict[str, Any]: Application configuration
        """
        return {
            "debug": self.get("app.debug", False),
            "log_level": self.get("app.log_level", "INFO"),
            "max_files_allowed": self.get("app.max_files_allowed", 50),
            "incremental_mode": self.get("app.incremental_mode", False),
            "logging_enabled": self.get("app.logging_enabled", True),
            "log_format": self.get("app.log_format", "simple"),
        }

    # Explicitly override clear_cache to satisfy the abstract method requirement
    # Even though CachingMixin provides this, we need to make it explicit for ABC
    def clear_cache(self) -> None:
        """Clear all cached settings.

        Implementation delegates to CachingMixin's clear_cache method.
        """
        # Directly call CachingMixin's implementation instead of using super()
        CachingMixin.clear_cache(self)


# Global settings service instance
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """Get or create the global settings service instance.

    Returns:
        SettingsService: The global settings service instance
    """
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
