import logging
from typing import Any
import os
from threading import RLock
from dynaconf import Dynaconf
from prdiffer.domain.services.settings import SettingsServiceInterface
from prdiffer.domain.config.github_config import GitHubConfig

logger = logging.getLogger(__name__)


class SettingsService(SettingsServiceInterface):
    """Settings service for reading TOML configuration files with Dynaconf.

    Uses manual caching with RLock for thread-safe operation
    because Dynaconf objects are unhashable (no @lru_cache).
    """

    def __init__(
        self,
        settings_files: list[str] | None = None,
    ) -> None:
        if settings_files is None:
            settings_files = ["settings.toml", ".secrets.toml"]

        self.settings = Dynaconf(
            settings_files=settings_files,
            environments=True,
            env_switcher="ENV_FOR_DYNACONF",
            load_dotenv=True,
        )

        self._cache_lock = RLock()
        self._github_settings_cache: dict[str, Any] | None = None
        self._github_config_cache: GitHubConfig | None = None
        self._cache_settings_cache: dict[str, Any] | None = None
        self._app_settings_cache: dict[str, Any] | None = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def get_str(self, key: str, default: str = "") -> str:
        value = self.settings.get(key, default)
        if isinstance(value, str):
            return value
        return str(value) if value is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        value = self.settings.get(key, default)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        try:
            return int(value) if value is not None else default
        except ValueError, TypeError:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.settings.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value) if value is not None else default

    def get_float(self, key: str, default: float = 0.0) -> float:
        value = self.settings.get(key, default)
        if isinstance(value, float):
            return value
        try:
            return float(value) if value is not None else default
        except ValueError, TypeError:
            return default

    def get_github_settings(self) -> dict[str, Any]:
        """Get GitHub-related settings with caching.

        GitHub token authentication is exclusively managed via the
        GITHUB_TOKEN environment variable, not from settings files.
        """
        with self._cache_lock:
            if self._github_settings_cache is not None:
                return self._github_settings_cache

            def get_with_fallback(key: str, default: Any = None) -> Any:
                value = self.get(key)
                if value is None and hasattr(self.settings, "from_env"):
                    default_settings = self.settings.from_env("default")
                    value = default_settings.get(key, default) if default_settings else default
                return value or default

            self._github_settings_cache = {
                "rate_limit": get_with_fallback("github.rate_limit", 5000),
                "timeout": get_with_fallback("github.timeout", 30),
                "max_retries": get_with_fallback("github.max_retries", 3),
                "retry_delay": get_with_fallback("github.retry_delay", 1),
                "retry_on_404": get_with_fallback("github.retry_on_404", False),
                "retry_on_403": get_with_fallback("github.retry_on_403", True),
                "retry_on_500": get_with_fallback("github.retry_on_500", True),
                "retry_log_level": get_with_fallback("github.retry_log_level", "DEBUG"),
                "permanent_failure_log_level": get_with_fallback("github.permanent_failure_log_level", "INFO"),
                "circuit_breaker_enabled": get_with_fallback("github.circuit_breaker_enabled", True),
                "circuit_breaker_failure_threshold": get_with_fallback("github.circuit_breaker_failure_threshold", 5),
                "circuit_breaker_timeout": get_with_fallback("github.circuit_breaker_timeout", 60),
                "adaptive_retry_enabled": get_with_fallback("github.adaptive_retry_enabled", True),
                "max_adaptive_delay": get_with_fallback("github.max_adaptive_delay", 30),
                "api_health_tracking": get_with_fallback("github.api_health_tracking", True),
                "context_aware_retry": get_with_fallback("github.context_aware_retry", True),
                "ignore_patterns": tuple(get_with_fallback("github.ignore_patterns", [])),
                "valid_extensions": tuple(get_with_fallback("github.valid_extensions", [])),
                "diff_parallel_enabled": get_with_fallback("github.diff_parallel_enabled", True),
                "diff_parallel_threshold": get_with_fallback("github.diff_parallel_threshold", 3),
                "diff_max_workers": get_with_fallback("github.diff_max_workers", 4),
                "diff_worker_timeout": get_with_fallback("github.diff_worker_timeout", 30.0),
                "max_concurrent": get_with_fallback("github.max_concurrent", 4),
            }
            return self._github_settings_cache

    def get_github_config(self) -> GitHubConfig:
        """Get centralized GitHub configuration as a GitHubConfig dataclass.

        Services should prefer receiving a GitHubConfig object
        instead of individual parameters.
        """
        with self._cache_lock:
            if self._github_config_cache is not None:
                return self._github_config_cache

            def get_with_fallback(key: str, default: Any = None) -> Any:
                value = self.get(key)
                if value is None and hasattr(self.settings, "from_env"):
                    default_settings = self.settings.from_env("default")
                    value = default_settings.get(key, default) if default_settings else None
                return value if value is not None else default

            self._github_config_cache = GitHubConfig(
                rate_limit=get_with_fallback("github.rate_limit", 5000),
                timeout=get_with_fallback("github.timeout", 30),
                max_retries=get_with_fallback("github.max_retries", 3),
                retry_delay=float(get_with_fallback("github.retry_delay", 1.0)),
                retry_on_404=get_with_fallback("github.retry_on_404", False),
                retry_on_403=get_with_fallback("github.retry_on_403", True),
                retry_on_500=get_with_fallback("github.retry_on_500", True),
                retry_log_level=get_with_fallback("github.retry_log_level", "DEBUG"),
                permanent_failure_log_level=get_with_fallback("github.permanent_failure_log_level", "INFO"),
                circuit_breaker_enabled=get_with_fallback("github.circuit_breaker_enabled", True),
                circuit_breaker_failure_threshold=get_with_fallback("github.circuit_breaker_failure_threshold", 5),
                circuit_breaker_timeout=get_with_fallback("github.circuit_breaker_timeout", 60),
                adaptive_retry_enabled=get_with_fallback("github.adaptive_retry_enabled", True),
                max_adaptive_delay=get_with_fallback("github.max_adaptive_delay", 30),
                api_health_tracking=get_with_fallback("github.api_health_tracking", True),
                context_aware_retry=get_with_fallback("github.context_aware_retry", True),
                ignore_patterns=tuple(get_with_fallback("github.ignore_patterns", [])),
                valid_extensions=tuple(get_with_fallback("github.valid_extensions", [])),
                diff_parallel_enabled=get_with_fallback("github.diff_parallel_enabled", True),
                diff_parallel_threshold=get_with_fallback("github.diff_parallel_threshold", 3),
                diff_max_workers=get_with_fallback("github.diff_max_workers", 4),
                diff_worker_timeout=float(get_with_fallback("github.diff_worker_timeout", 30.0)),
                max_files_allowed=get_with_fallback("app.max_files_allowed", 50),
                large_file_threshold=get_with_fallback("diff.large_file_threshold", 5000),
                chunk_size=get_with_fallback("diff.chunk_size", 1000),
                max_diff_size=get_with_fallback("diff.max_diff_size", 100000),
            )
            return self._github_config_cache

    def get_cache_settings(self) -> dict[str, Any]:
        with self._cache_lock:
            if self._cache_settings_cache is not None:
                return self._cache_settings_cache

            self._cache_settings_cache = {
                "ttl": self.get("cache.ttl", 300),
                "max_size": self.get("cache.max_size", 1000),
                "enabled": self.get("cache.enabled", True),
            }
            return self._cache_settings_cache

    def get_app_settings(self) -> dict[str, Any]:
        with self._cache_lock:
            if self._app_settings_cache is not None:
                return self._app_settings_cache

            self._app_settings_cache = {
                "debug": self.get("app.debug", False),
                "log_level": self.get("app.log_level", "INFO"),
                "max_files_allowed": self.get("app.max_files_allowed", 50),
                "incremental_mode": self.get("app.incremental_mode", False),
                "logging_enabled": self.get("app.logging_enabled", True),
                "log_format": self.get("app.log_format", "simple"),
            }
            return self._app_settings_cache

    def get_configuration_warnings(self) -> list[str]:
        warnings: list[str] = []

        try:
            rate_limit = self.get("github.rate_limit", 5000)
            if rate_limit > 5000:
                warnings.append(f"High rate limit ({rate_limit}) may cause API throttling")

            timeout = self.get("github.timeout", 30)
            if timeout < 10:
                warnings.append(f"Low timeout ({timeout}s) may cause premature failures")

            max_retries = self.get("github.max_retries", 3)
            if max_retries > 10:
                warnings.append(f"High retry count ({max_retries}) may increase latency")

            github_token = os.getenv("GITHUB_TOKEN")
            if not github_token:
                warnings.append("GITHUB_TOKEN environment variable not set - using anonymous access")

            use_hashed_keys = self.get("cache.use_hashed_keys", True)
            if not use_hashed_keys:
                warnings.append("Cache key hashing disabled - may use more memory")

        except Exception as e:
            logger.error(
                "Error checking configuration settings",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            warnings.append(f"Error checking configuration: {e}")

        return warnings

    def is_development_mode(self) -> bool:
        return self.get("app.debug", False) or os.getenv("ENV_FOR_DYNACONF") == "development"

    def _get_loaded_config_files(self) -> list[str]:
        try:
            if hasattr(self.settings, "_loaded_files"):
                return list(self.settings._loaded_files)
            elif hasattr(self.settings, "settings_files"):
                return list(self.settings.settings_files)
            else:
                return []
        except AttributeError, TypeError, KeyError:
            return []

    def clear_cache(self) -> None:
        """Clear all cached settings in a thread-safe manner."""
        with self._cache_lock:
            self._github_settings_cache = None
            self._github_config_cache = None
            self._cache_settings_cache = None
            self._app_settings_cache = None


_settings_service: SettingsService | None = None


def get_settings_service() -> SettingsService:
    """Get or create the global settings service singleton."""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
