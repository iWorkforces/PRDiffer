"""Factory for creating FastMCPServer with all dependencies properly injected."""

from typing import Optional

from ccpragents.domain.services.pr_diff_service import PRDiffServiceInterface

from .mcp_server import FastMCPServer
from ccpragents.domain.services.settings import SettingsServiceInterface
from ccpragents.domain.services.cache import CacheServiceInterface
from ccpragents.domain.services.repository_cache import RepositoryCacheServiceInterface
from ccpragents.domain.services.logger import LoggerServiceInterface

# Infrastructure factory
from ccpragents.infrastructure.factories import get_infrastructure_factory

# Legacy support
import logging


def create_mcp_server(
    github_repository_class,
    settings_service: Optional[SettingsServiceInterface] = None,
    cache_service: Optional[CacheServiceInterface] = None,
    repository_cache_service: Optional[RepositoryCacheServiceInterface] = None,
    pr_diff_service: Optional[PRDiffServiceInterface] = None,
    logger: Optional[LoggerServiceInterface] = None,
) -> FastMCPServer:
    """Create FastMCPServer with all dependencies properly injected.

    This factory function creates and wires all the necessary components
    for the FastMCPServer using the infrastructure factory pattern,
    ensuring proper dependency injection and Clean Architecture compliance.

    Args:
        github_repository_class: Class for creating GitHub repository instances
        settings_service: Optional Settings service for configuration (created if None)
        cache_service: Optional Cache service for storing PR data (created if None)
        repository_cache_service: Optional Repository cache service (created if None)
        logger: Optional LoggerServiceInterface instance (created if None)

    Returns:
        Fully configured FastMCPServer instance
    """
    # Use infrastructure factory to create services if not provided
    infrastructure_factory = get_infrastructure_factory()

    if settings_service is None:
        settings_service = infrastructure_factory.create_settings_service()

    if logger is None:
        logger = infrastructure_factory.create_logger_service()

    if cache_service is None:
        cache_service = infrastructure_factory.create_cache_service()

    if repository_cache_service is None:
        repository_cache_service = (
            infrastructure_factory.create_repository_cache_service()
        )

    # Create application layer components via infrastructure factory
    url_validator = infrastructure_factory.create_url_validator(logger)
    rate_limiter = infrastructure_factory.create_rate_limiter(logger)
    metrics_tracker = infrastructure_factory.create_metrics_tracker(logger)
    server_configuration = infrastructure_factory.create_server_configuration(
        settings_service, logger
    )

    # Create PR operation handler with all its dependencies
    pr_operation_handler = infrastructure_factory.create_pr_operation_handler(
        github_repository_class=github_repository_class,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        diff_service=infrastructure_factory.create_diff_service(),
        pattern_matching_service=infrastructure_factory.create_pattern_matching_service(),
        retry_service=infrastructure_factory.create_retry_service(),
        logger=logger,
    )

    # Create health monitor with dependencies
    health_monitor = infrastructure_factory.create_health_monitor(
        metrics_tracker=metrics_tracker,
        rate_limiter=rate_limiter,
        logger=logger,
    )

    # Create infrastructure services that need to be injected
    # Import infrastructure services for injection
    from ccpragents.infrastructure.security.input_validator import InputValidator
    from ccpragents.infrastructure.request_coalescing import (
        get_request_coalescing_service,
    )

    # Create PR diff service if not provided
    if pr_diff_service is None:
        pr_diff_service = infrastructure_factory.create_pr_diff_service()

    input_validator_instance = InputValidator()
    request_coalescing_instance = get_request_coalescing_service()

    # Create and return the main server with all components injected
    return FastMCPServer(
        settings_service=settings_service,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        pr_diff_service=pr_diff_service,
        github_repository_class=github_repository_class,
        logger=logger,
        # Injected components from infrastructure factory
        url_validator=url_validator,
        rate_limiter=rate_limiter,
        metrics_tracker=metrics_tracker,
        pr_operation_handler=pr_operation_handler,
        health_monitor=health_monitor,
        server_configuration=server_configuration,
        # Security and request coalescing services - injected instances
        input_validator=input_validator_instance,
        request_coalescing_service=request_coalescing_instance,
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
        from ccpragents.infrastructure.logging.console_logger import get_logger

        logger_service = get_logger()
    else:
        # For legacy compatibility, if a logging.Logger is passed, use get_logger instead
        from ccpragents.infrastructure.logging.console_logger import get_logger

        logger_service = get_logger()

    # Create infrastructure factory to get PR diff service
    infrastructure_factory = get_infrastructure_factory()

    # Create all required infrastructure components
    pr_diff_service = infrastructure_factory.create_pr_diff_service()
    url_validator = infrastructure_factory.create_url_validator(logger_service)
    rate_limiter = infrastructure_factory.create_rate_limiter(logger_service)
    metrics_tracker = infrastructure_factory.create_metrics_tracker(logger_service)
    pr_operation_handler = infrastructure_factory.create_pr_operation_handler(
        github_repository_class=github_repository_class,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        diff_service=infrastructure_factory.create_diff_service(),
        pattern_matching_service=infrastructure_factory.create_pattern_matching_service(),
        retry_service=infrastructure_factory.create_retry_service(),
        logger=logger_service,
    )
    health_monitor = infrastructure_factory.create_health_monitor(
        metrics_tracker=metrics_tracker,
        rate_limiter=rate_limiter,
        logger=logger_service,
    )
    server_configuration = infrastructure_factory.create_server_configuration(
        settings_service, logger_service
    )

    return FastMCPServer(
        settings_service=settings_service,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        pr_diff_service=pr_diff_service,
        logger=logger_service,
        github_repository_class=github_repository_class,
        url_validator=url_validator,
        rate_limiter=rate_limiter,
        metrics_tracker=metrics_tracker,
        pr_operation_handler=pr_operation_handler,
        health_monitor=health_monitor,
        server_configuration=server_configuration,
    )
