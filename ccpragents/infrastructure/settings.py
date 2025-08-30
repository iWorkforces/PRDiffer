from typing import Optional, Dict, Any, cast
from dynaconf import Dynaconf
from ccpragents.domain.services import SettingsServiceInterface


class SettingsService(SettingsServiceInterface):
    """Settings service for reading TOML configuration files with Dynaconf and caching.

    This service provides a centralized way to access application settings with
    built-in caching for maximum performance.

    Attributes:
        settings: The Dynaconf instance for configuration management
    """

    def __init__(self, settings_files: Optional[list] = None):
        """Initialize the settings service with configuration files.

        Args:
            settings_files: List of TOML files to load. Defaults to ['settings.toml', '.secrets.toml']
        """
        if settings_files is None:
            settings_files = ['settings.toml', '.secrets.toml']

        self.settings = Dynaconf(
            settings_files=settings_files,
            environments=True,
            env_switcher='ENV_FOR_DYNACONF',
            envvar_prefix='CCPRDIFF',
            load_dotenv=True,
        )

        # Manual caching to avoid @lru_cache issues with unhashable instance
        self._cache = {}
        self._github_settings_cache = None
        self._cache_settings_cache = None
        self._app_settings_cache = None

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with caching.

        Args:
            key: The configuration key to retrieve
            default: Default value if key is not found

        Returns:
            Any: The configuration value or default
        """
        # Make cache key hashable by converting lists to tuples
        hashable_default = tuple(default) if isinstance(default, list) else default
        cache_key = (key, hashable_default)
        if cache_key not in self._cache:
            # Use cast to tell type checker that settings.get returns the expected type
            self._cache[cache_key] = cast(Any, self.settings.get(key, default))  # type: ignore[misc]
        return self._cache[cache_key]

    def get_github_settings(self) -> Dict[str, Any]:
        """Get GitHub-related settings with caching.

        Returns:
            Dict[str, Any]: GitHub configuration including token, rate limits, etc.
        """
        if self._github_settings_cache is None:
            # Get settings from current environment, fall back to default environment if not found
            def get_with_fallback(key, default=None):
                value = self.get(key)
                if value is None and hasattr(self.settings, 'from_env'):
                    # Fall back to default environment
                    default_settings = cast(Dynaconf, self.settings.from_env('default'))  # type: ignore[misc]
                    value = cast(Any, default_settings.get(key, default))  # type: ignore[misc]
                return value or default

            self._github_settings_cache = {
                'token': self.get('github_token') or self.get('github.token'),
                'rate_limit': get_with_fallback('github.rate_limit', 5000),
                'timeout': get_with_fallback('github.timeout', 30),
                'max_retries': get_with_fallback('github.max_retries', 3),
                'retry_delay': get_with_fallback('github.retry_delay', 1),
                'ignore_patterns': tuple(get_with_fallback('github.ignore_patterns', [])),
                'valid_extensions': tuple(get_with_fallback('github.valid_extensions', [])),
            }
        return self._github_settings_cache

    def get_cache_settings(self) -> Dict[str, Any]:
        """Get cache-related settings with caching.

        Returns:
            Dict[str, Any]: Cache configuration including TTL and size limits
        """
        if self._cache_settings_cache is None:
            self._cache_settings_cache = {
                'ttl': self.get('cache.ttl', 300),  # 5 minutes default
                'max_size': self.get('cache.max_size', 1000),
                'enabled': self.get('cache.enabled', True),
            }
        return self._cache_settings_cache

    def get_app_settings(self) -> Dict[str, Any]:
        """Get general application settings with caching.

        Returns:
            Dict[str, Any]: Application configuration
        """
        if self._app_settings_cache is None:
            self._app_settings_cache = {
                'debug': self.get('app.debug', False),
                'log_level': self.get('app.log_level', 'INFO'),
                'max_files_allowed': self.get('app.max_files_allowed', 50),
                'incremental_mode': self.get('app.incremental_mode', False),
                'logging_enabled': self.get('app.logging_enabled', True),
                'log_format': self.get('app.log_format', 'simple'),
            }
        return self._app_settings_cache

    def clear_cache(self):
        """Clear all cached settings."""
        self._cache.clear()
        self._github_settings_cache = None
        self._cache_settings_cache = None
        self._app_settings_cache = None


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
