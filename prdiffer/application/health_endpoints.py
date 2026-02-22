"""Health endpoints module for FastMCP server.

This module extracts health and metrics endpoints from mcp_server.py,
providing monitoring and observability functionality.
"""

from collections.abc import Callable, Awaitable

from starlette.requests import Request
from starlette.responses import JSONResponse

from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.repository_cache import RepositoryCacheServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.interfaces.protocols import (
    MetricsTrackerProtocol,
    HealthMonitorProtocol,
    AuthenticationProtocol,
)
from prdiffer.infrastructure.utils.coalescing import RequestCoalescingService


class HealthEndpoints:
    """Handler for health and metrics endpoints.

    This class provides health status and metrics tracking
    for the MCP server.

    Attributes:
        health_monitor: Health monitor for component status
        metrics_tracker: Metrics tracker for performance metrics
        cache_service: Cache service for stats
        repository_cache_service: Repository cache service for stats
        authentication: Authentication service for status
        request_coalescing: Request coalescing service for stats
        logger: Logger for health check logging
    """

    def __init__(
        self,
        health_monitor: HealthMonitorProtocol,
        metrics_tracker: MetricsTrackerProtocol,
        cache_service: CacheServiceInterface,
        repository_cache_service: RepositoryCacheServiceInterface,
        authentication: AuthenticationProtocol,
        request_coalescing: RequestCoalescingService,
        logger: LoggerServiceInterface,
    ):
        """Initialize HealthEndpoints with dependencies.

        Args:
            health_monitor: Health monitor protocol
            metrics_tracker: Metrics tracker protocol
            cache_service: Cache service instance
            repository_cache_service: Repository cache service instance
            authentication: Authentication protocol
            request_coalescing: Request coalescing service
            logger: Logger instance
        """
        self._health_monitor = health_monitor
        self._metrics_tracker = metrics_tracker
        self._cache_service = cache_service
        self._repository_cache_service = repository_cache_service
        self._authentication = authentication
        self._request_coalescing = request_coalescing
        self._logger = logger

    async def _get_health_status(self) -> dict:
        """Get health status and metrics for the MCP server.

        Returns:
            dict: Health status and metrics information
        """
        health_status = self._health_monitor.check_health()
        health_status["authentication"] = self._authentication.get_status()
        health_status["cache"] = self._cache_service.get_stats()
        health_status["repository_cache"] = self._repository_cache_service.stats()
        health_status["request_coalescing"] = await self._request_coalescing.get_stats()
        return health_status

    def get_health_handler(self) -> Callable[[], Awaitable[dict]]:
        """Get health check handler function.

        This returns the actual health handler function that can be
        registered with FastMCP.

        Returns:
            callable: Health check handler function
        """

        async def health():
            """Get server health status and metrics.

            Returns:
                dict: Health status and performance metrics
            """
            try:
                return await self._get_health_status()
            except (RuntimeError, KeyError, AttributeError) as e:
                self._logger.error(
                    "Failed to get health status",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                safe_message = self._create_safe_error_message(e)
                return {"status": "unhealthy", "error": safe_message}

        return health

    def get_metrics_handler(self) -> Callable[[Request], Awaitable[JSONResponse]]:
        """Get metrics handler function.

        This returns the actual metrics handler function that can be
        registered with FastMCP.

        Returns:
            callable: Metrics handler function
        """

        async def metrics_handler(request: Request) -> JSONResponse:
            """Handle metrics endpoint requests.

            Args:
                request: FastAPI Request object

            Returns:
                JSONResponse with metrics summary
            """
            try:
                metrics = self._metrics_tracker.get_metrics_summary()
                return JSONResponse(metrics)
            except (RuntimeError, KeyError, AttributeError) as e:
                self._logger.error(
                    "Failed to get metrics",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return JSONResponse(
                    {
                        "server": "prdiffer",
                        "error": "Failed to get metrics",
                        "message": "Internal server error",
                    },
                    status_code=500,
                )

        return metrics_handler

    def _create_safe_error_message(self, exception: Exception) -> str:
        """Create a safe error message that doesn't expose internal details.

        Args:
            exception: The exception to create a safe message for

        Returns:
            str: A safe error message suitable for external consumption
        """
        safe_messages = {
            "GithubException": "GitHub API error occurred",
            "RateLimitExceededException": "API rate limit exceeded. Please try again later",
            "UnknownObjectException": "Repository or PR not found",
            "BadCredentialsException": "GitHub authentication failed",
            "TwoFactorException": "Two-factor authentication required",
            "InvalidURLError": "Invalid GitHub PR URL format",
            "InvalidRepositoryError": "Invalid repository identifier",
            "InvalidPRNumberError": "Invalid pull request number",
            "InputSanitizationError": "Invalid input parameters",
            "SuspiciousOperationError": "Request contains suspicious patterns",
            "ConnectionError": "Connection to GitHub failed",
            "TimeoutError": "Request timed out",
            "SSLError": "Secure connection failed",
            "ValueError": "Invalid input value",
            "TypeError": "Invalid input type",
            "KeyError": "Missing required field",
            "AttributeError": "Configuration error",
        }

        exception_type = type(exception).__name__

        if exception_type in safe_messages:
            return safe_messages[exception_type]

        return "Request processing failed"
