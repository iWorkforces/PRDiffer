"""Factory for creating FastMCPServer with all dependencies properly injected."""

import logging
from typing import Optional

from .mcp_server import FastMCPServer
from ccpragents.infrastructure.logging.console_logger import get_logger
from .components.url_validator import URLValidator
from .components.rate_limiter import RateLimiter
from .components.metrics_tracker import MetricsTracker
from .components.pr_operation_handler import PROperationHandler
from .components.health_monitor import HealthMonitor
from .components.server_configuration import ServerConfiguration

from ccpragents.domain.services.settings import SettingsServiceInterface
from ccpragents.domain.services.cache import CacheServiceInterface
from ccpragents.domain.services.repository_cache import RepositoryCacheServiceInterface
from ccpragents.domain.services.logger import LoggerServiceInterface


def create_mcp_server(
    github_repository_class,
    settings_service: SettingsServiceInterface,
    cache_service: CacheServiceInterface,
    repository_cache_service: RepositoryCacheServiceInterface,
    logger: Optional[LoggerServiceInterface] = None,
) -> FastMCPServer:
    """Create FastMCPServer with all dependencies properly injected.

    This factory function creates and wires all the necessary components
    for the FastMCPServer, ensuring proper dependency injection and
    maintaining the same interface as the original monolithic class.

    Args:
        github_repository_class: Class for creating GitHub repository instances
        settings_service: Settings service for configuration
        cache_service: Cache service for storing PR data
        repository_cache_service: Repository cache service
        logger: Optional LoggerServiceInterface instance

    Returns:
        Fully configured FastMCPServer instance
    """
    if logger is None:
        logger = get_logger()

    # Create base components
    url_validator = URLValidator()
    rate_limiter = RateLimiter(logger=logger)
    metrics_tracker = MetricsTracker(logger=logger)
    server_configuration = ServerConfiguration(settings_service, logger=logger)

    # Create PR operation handler with all its dependencies
    pr_operation_handler = PROperationHandler(
        github_repository_class=github_repository_class,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        logger=logger,
    )

    # Create health monitor with dependencies
    health_monitor = HealthMonitor(
        metrics_tracker=metrics_tracker, rate_limiter=rate_limiter, logger=logger
    )

    # Create and return the main server with all components injected
    return FastMCPServer(
        settings_service=settings_service,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        github_repository_class=github_repository_class,
        logger=logger,
        # Injected components
        url_validator=url_validator,
        rate_limiter=rate_limiter,
        metrics_tracker=metrics_tracker,
        pr_operation_handler=pr_operation_handler,
        health_monitor=health_monitor,
        server_configuration=server_configuration,
    )


def create_mcp_server_legacy(
    github_repository_class,
    settings_service: SettingsServiceInterface,
    cache_service: CacheServiceInterface,
    repository_cache_service: RepositoryCacheServiceInterface,
    logger: Optional[logging.Logger] = None,
) -> FastMCPServer:
    """Create FastMCPServer using the legacy constructor (for backward compatibility).

    This function maintains backward compatibility by using the original
    constructor signature, allowing existing code to work without changes
    during the migration period.

    Args:
        Same as create_mcp_server

    Returns:
        FastMCPServer instance created with legacy constructor
    """
    # Convert logging.Logger to LoggerServiceInterface for backward compatibility
    if logger is None:
        logger_service = get_logger()
    else:
        # For legacy compatibility, if a logging.Logger is passed, use get_logger instead
        logger_service = get_logger()

    return FastMCPServer(
        settings_service=settings_service,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        github_repository_class=github_repository_class,
        logger=logger_service,
    )
