"""Application service for health check operations.

This service provides health monitoring and metrics collection for the
application, aggregating information from various infrastructure services.
"""

from typing import Dict, Any
from datetime import datetime
from abc import ABC, abstractmethod

from ccpragents.domain.services.logger import LoggerServiceInterface
from ccpragents.domain.services.settings import SettingsServiceInterface
from ccpragents.domain.services.cache import CacheServiceInterface
from ccpragents.domain.services.repository_cache import RepositoryCacheServiceInterface


class HealthCheckApplicationServiceInterface(ABC):
    """Abstract interface for health check application service."""

    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the application.

        Returns:
            Dict[str, Any]: Health status information
        """
        pass

    @abstractmethod
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics.

        Returns:
            Dict[str, Any]: System metrics
        """
        pass

    @abstractmethod
    def get_service_dependencies(self) -> Dict[str, Any]:
        """Get status of external service dependencies.

        Returns:
            Dict[str, Any]: Service dependency status
        """
        pass

    @abstractmethod
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache system status.

        Returns:
            Dict[str, Any]: Cache status information
        """
        pass


class HealthCheckApplicationService(HealthCheckApplicationServiceInterface):
    """Concrete implementation of health check application service."""

    def __init__(
        self,
        settings_service: SettingsServiceInterface,
        logger: LoggerServiceInterface,
        cache_service: CacheServiceInterface,
        repository_cache_service: RepositoryCacheServiceInterface,
    ):
        """Initialize the health check service.

        Args:
            settings_service: Settings service for configuration
            logger: Logger service for structured logging
            cache_service: Cache service for cache status
            repository_cache_service: Repository cache service for repository cache status
        """
        self._settings_service = settings_service
        self._logger = logger
        self._cache_service = cache_service
        self._repository_cache_service = repository_cache_service

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the application.

        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            cache_status = self.get_cache_status()
            service_deps = self.get_service_dependencies()
            system_metrics = self.get_system_metrics()

            # Determine overall health
            cache_healthy = cache_status.get("status") == "healthy"
            deps_healthy = all(
                dep.get("status") == "healthy" for dep in service_deps.values()
            )

            overall_status = (
                "healthy" if (cache_healthy and deps_healthy) else "unhealthy"
            )

            health_info = {
                "status": overall_status,
                "timestamp": datetime.now().isoformat(),
                "version": "0.1.3",
                "service_name": "ccpragents",
                "cache": cache_status,
                "dependencies": service_deps,
                "metrics": system_metrics,
                "uptime_seconds": system_metrics.get("uptime_seconds", 0),
            }

            self._logger.info(
                "Health check completed",
                status=overall_status,
                cache_status=cache_status.get("status"),
                dependencies_status="healthy" if deps_healthy else "unhealthy",
            )

            return health_info

        except Exception as e:
            self._logger.error(
                "Health check failed", error=str(e), error_type=type(e).__name__
            )

            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "service_name": "ccpragents",
            }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics.

        Returns:
            Dict[str, Any]: System metrics
        """
        try:
            # Get basic system information
            import time
            import psutil
            import sys
            import platform

            # Calculate uptime
            boot_time = psutil.boot_time()
            current_time = time.time()
            uptime_seconds = current_time - boot_time

            # Get memory usage
            memory = psutil.virtual_memory()
            memory_info = {
                "total_mb": round(memory.total / 1024 / 1024, 2),
                "available_mb": round(memory.available / 1024 / 1024, 2),
                "used_percent": memory.percent,
            }

            # Get CPU usage
            cpu_count = psutil.cpu_count()
            cpu_usage = psutil.cpu_percent(interval=1)

            # Get disk usage
            disk = psutil.disk_usage("/")
            disk_info = {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "used_percent": round((disk.used / disk.total) * 100, 2),
            }

            metrics = {
                "uptime_seconds": round(uptime_seconds, 2),
                "memory": memory_info,
                "cpu": {
                    "count": cpu_count,
                    "usage_percent": cpu_usage,
                },
                "disk": disk_info,
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "python_version": sys.version.split()[0],
                },
                "timestamp": datetime.now().isoformat(),
            }

            return metrics

        except Exception as e:
            self._logger.error(
                "Failed to get system metrics",
                error=str(e),
                error_type=type(e).__name__,
            )

            return {
                "error": f"Failed to get system metrics: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def get_service_dependencies(self) -> Dict[str, Any]:
        """Get status of external service dependencies.

        Returns:
            Dict[str, Any]: Service dependency status
        """
        dependencies = {}

        # Check GitHub API availability
        try:
            # This would normally check actual GitHub API connectivity
            # For now, we'll simulate the check
            github_token = self._settings_service.get("github.token", None)

            dependencies["github_api"] = {
                "name": "GitHub API",
                "status": "healthy" if github_token else "warning",
                "endpoint": "api.github.com",
                "authenticated": bool(github_token),
                "rate_limit": self._settings_service.get("github.rate_limit", 5000),
                "timeout": self._settings_service.get("github.timeout", 30),
                "last_check": datetime.now().isoformat(),
            }

        except Exception as e:
            dependencies["github_api"] = {
                "name": "GitHub API",
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat(),
            }

        # Check settings service
        try:
            # Verify settings are accessible
            debug_mode = self._settings_service.get("app.debug", False)
            dependencies["settings"] = {
                "name": "Settings Service",
                "status": "healthy",
                "debug_mode": debug_mode,
                "last_check": datetime.now().isoformat(),
            }

        except Exception as e:
            dependencies["settings"] = {
                "name": "Settings Service",
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat(),
            }

        return dependencies

    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache system status.

        Returns:
            Dict[str, Any]: Cache status information
        """
        try:
            cache_stats = self._cache_service.get_stats()
            repo_cache_stats = self._repository_cache_service.stats()

            # Determine cache health
            cache_entries = cache_stats.get("size", 0)
            repo_cache_entries = repo_cache_stats.get("size", 0)

            status = "healthy"
            if cache_entries == 0 and repo_cache_entries == 0:
                status = "warning"  # No cached data but service is working

            cache_info = {
                "status": status,
                "main_cache": {
                    "entries": cache_entries,
                    "size": cache_stats.get("size", 0),
                    "hit_rate": cache_stats.get("hit_rate", 0),
                    "memory_usage": cache_stats.get("memory_usage", "unknown"),
                },
                "repository_cache": {
                    "entries": repo_cache_entries,
                    "size": repo_cache_stats.get("size", 0),
                    "hit_rate": repo_cache_stats.get("hit_rate", 0),
                },
                "last_update": datetime.now().isoformat(),
            }

            return cache_info

        except Exception as e:
            self._logger.error(
                "Failed to get cache status", error=str(e), error_type=type(e).__name__
            )

            return {
                "status": "error",
                "error": str(e),
                "last_update": datetime.now().isoformat(),
            }
