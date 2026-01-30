from abc import ABC, abstractmethod
from typing import Any


class SettingsServiceInterface(ABC):
    """Abstract base class for settings services.

    This interface defines the contract for settings services that provide
    configuration management with caching capabilities.
    """

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with caching.

        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found

        Returns:
            Any: The configuration value or default
        """
        pass

    @abstractmethod
    def get_github_settings(self) -> dict[str, Any]:
        """Get GitHub-related settings with proper type conversion.

        Returns:
            dict[str, Any]: GitHub settings including token, ignore_patterns, valid_extensions
        """
        pass

    @abstractmethod
    def get_cache_settings(self) -> dict[str, Any]:
        """Get cache-related settings.

        Returns:
            dict[str, Any]: Cache settings including TTL and size limits
        """
        pass

    @abstractmethod
    def get_app_settings(self) -> dict[str, Any]:
        """Get application-specific settings.

        Returns:
            dict[str, Any]: Application settings including max_files_allowed
        """
        pass

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear all cached settings."""
        pass
