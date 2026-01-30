"""Factory for creating FastMCPServer with all dependencies properly injected."""

from typing import Optional

from prdiffer.domain.services.pr_diff_service import PRDiffServiceInterface

from .mcp_server import FastMCPServer
from prdiffer.domain.services.settings import SettingsServiceInterface
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.repository_cache import RepositoryCacheServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface

from prdiffer.infrastructure.factories import get_infrastructure_factory
from prdiffer.application.factories import get_application_factory

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
    infrastructure_factory = get_infrastructure_factory()
    application_factory = get_application_factory()

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

    rate_limiter = application_factory.create_rate_limiter(logger)
    metrics_tracker = application_factory.create_metrics_tracker(logger)
    server_configuration = application_factory.create_server_configuration(
        settings_service, logger
    )
    authentication = application_factory.create_authentication(logger)

    pr_operation_handler = application_factory.create_pr_operation_handler(
        github_repository_class=github_repository_class,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        diff_service=infrastructure_factory.create_diff_service(),
        pattern_matching_service=infrastructure_factory.create_pattern_matching_service(),
        retry_service=infrastructure_factory.create_retry_service(),
        logger=logger,
    )

    health_monitor = application_factory.create_health_monitor(
        metrics_tracker=metrics_tracker,
        rate_limiter=rate_limiter,
        logger=logger,
    )

    from prdiffer.infrastructure.security.input_validator import InputValidator
    from prdiffer.infrastructure.request_coalescing import (
        get_request_coalescing_service,
    )

    if pr_diff_service is None:
        pr_diff_service = infrastructure_factory.create_pr_diff_service()

    input_validator_instance = InputValidator()
    request_coalescing_instance = get_request_coalescing_service()

    return FastMCPServer(
        settings_service=settings_service,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        pr_diff_service=pr_diff_service,
        github_repository_class=github_repository_class,
        logger=logger,
        rate_limiter=rate_limiter,
        metrics_tracker=metrics_tracker,
        pr_operation_handler=pr_operation_handler,
        health_monitor=health_monitor,
        server_configuration=server_configuration,
        authentication=authentication,
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
    if logger is None:
        from prdiffer.infrastructure.logging.console_logger import get_logger

        logger_service = get_logger()
    else:
        from prdiffer.infrastructure.logging.console_logger import get_logger

        logger_service = get_logger()

    infrastructure_factory = get_infrastructure_factory()
    application_factory = get_application_factory()

    pr_diff_service = infrastructure_factory.create_pr_diff_service()
    rate_limiter = application_factory.create_rate_limiter(logger_service)
    metrics_tracker = application_factory.create_metrics_tracker(logger_service)
    authentication = application_factory.create_authentication(logger_service)
    pr_operation_handler = application_factory.create_pr_operation_handler(
        github_repository_class=github_repository_class,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        diff_service=infrastructure_factory.create_diff_service(),
        pattern_matching_service=infrastructure_factory.create_pattern_matching_service(),
        retry_service=infrastructure_factory.create_retry_service(),
        logger=logger_service,
    )
    health_monitor = application_factory.create_health_monitor(
        metrics_tracker=metrics_tracker,
        rate_limiter=rate_limiter,
        logger=logger_service,
    )
    server_configuration = application_factory.create_server_configuration(
        settings_service, logger_service
    )

    return FastMCPServer(
        settings_service=settings_service,
        cache_service=cache_service,
        repository_cache_service=repository_cache_service,
        pr_diff_service=pr_diff_service,
        logger=logger_service,
        github_repository_class=github_repository_class,
        rate_limiter=rate_limiter,
        metrics_tracker=metrics_tracker,
        pr_operation_handler=pr_operation_handler,
        health_monitor=health_monitor,
        server_configuration=server_configuration,
        authentication=authentication,
    )
