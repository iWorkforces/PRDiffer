"""Concrete application factory implementation for creating application-layer components."""

from typing import Any

from prdiffer.domain.factories.application_factory import ApplicationFactoryInterface
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.services.settings import SettingsServiceInterface
from prdiffer.domain.services.repository_cache import RepositoryCacheServiceInterface
from prdiffer.domain.services.diff import DiffServiceInterface
from prdiffer.domain.services.pattern_matching import PatternMatchingServiceInterface
from prdiffer.domain.services.retry import RetryServiceInterface

from prdiffer.domain.interfaces.protocols import (
    RateLimiterProtocol,
    MetricsTrackerProtocol,
    PROperationHandlerProtocol,
    HealthMonitorProtocol,
    ServerConfigurationProtocol,
    AuthenticationProtocol,
)

from prdiffer.application.components.rate_limiter import RateLimiter
from prdiffer.application.components.metrics_tracker import MetricsTracker
from prdiffer.application.components.pr_operation_handler import PROperationHandler
from prdiffer.application.components.health_monitor import HealthMonitor
from prdiffer.application.components.server_configuration import ServerConfiguration
from prdiffer.application.components.authentication import AuthenticationMiddleware
from prdiffer.domain.interfaces.input_validation import InputValidatorProtocol


class ApplicationFactory(ApplicationFactoryInterface):
    """Concrete implementation of application factory for creating application-layer components."""

    def create_rate_limiter(self, logger: LoggerServiceInterface) -> RateLimiterProtocol:
        return RateLimiter(logger=logger)

    def create_metrics_tracker(self, logger: LoggerServiceInterface) -> MetricsTrackerProtocol:
        return MetricsTracker(logger=logger)

    def create_pr_operation_handler(
        self,
        github_repository_class: Any,
        cache_service: CacheServiceInterface,
        repository_cache_service: RepositoryCacheServiceInterface,
        diff_service: DiffServiceInterface,
        pattern_matching_service: PatternMatchingServiceInterface,
        retry_service: RetryServiceInterface,
        logger: LoggerServiceInterface,
        input_validator: InputValidatorProtocol | None = None,
    ) -> PROperationHandlerProtocol:
        if input_validator is None:
            from prdiffer.infrastructure.factories.infrastructure_factory import get_infrastructure_factory

            input_validator = get_infrastructure_factory().create_input_validator()
        return PROperationHandler(
            github_repository_class=github_repository_class,
            cache_service=cache_service,
            repository_cache_service=repository_cache_service,
            logger=logger,
            input_validator=input_validator,
        )

    def create_health_monitor(
        self,
        metrics_tracker: MetricsTrackerProtocol,
        rate_limiter: RateLimiterProtocol,
        logger: LoggerServiceInterface,
    ) -> HealthMonitorProtocol:
        return HealthMonitor(
            metrics_tracker=metrics_tracker,
            rate_limiter=rate_limiter,
            logger=logger,
        )

    def create_server_configuration(
        self,
        settings_service: SettingsServiceInterface,
        logger: LoggerServiceInterface,
    ) -> ServerConfigurationProtocol:
        return ServerConfiguration(
            settings_service=settings_service,
            logger=logger,
        )

    def create_authentication(self, logger: LoggerServiceInterface) -> AuthenticationProtocol:
        return AuthenticationMiddleware(logger=logger)


_application_factory: ApplicationFactory | None = None


def get_application_factory() -> ApplicationFactoryInterface:
    """Get singleton instance of the application factory."""
    global _application_factory
    if _application_factory is None:
        _application_factory = ApplicationFactory()
    return _application_factory
