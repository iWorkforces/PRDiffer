"""Application factory interface defining contracts for application-layer component creation."""

from abc import ABC, abstractmethod
from typing import Any

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


class ApplicationFactoryInterface(ABC):
    """Abstract factory for creating application-layer components (rate limiting, metrics, auth, health)."""

    @abstractmethod
    def create_rate_limiter(self, logger: LoggerServiceInterface) -> RateLimiterProtocol:
        pass

    @abstractmethod
    def create_metrics_tracker(self, logger: LoggerServiceInterface) -> MetricsTrackerProtocol:
        pass

    @abstractmethod
    def create_pr_operation_handler(
        self,
        github_repository_class: Any,
        cache_service: CacheServiceInterface,
        repository_cache_service: RepositoryCacheServiceInterface,
        diff_service: DiffServiceInterface,
        pattern_matching_service: PatternMatchingServiceInterface,
        retry_service: RetryServiceInterface,
        logger: LoggerServiceInterface,
        input_validator: Any = None,
    ) -> PROperationHandlerProtocol:
        pass

    @abstractmethod
    def create_health_monitor(
        self,
        metrics_tracker: MetricsTrackerProtocol,
        rate_limiter: RateLimiterProtocol,
        logger: LoggerServiceInterface,
    ) -> HealthMonitorProtocol:
        pass

    @abstractmethod
    def create_server_configuration(
        self,
        settings_service: SettingsServiceInterface,
        logger: LoggerServiceInterface,
    ) -> ServerConfigurationProtocol:
        pass

    @abstractmethod
    def create_authentication(self, logger: LoggerServiceInterface) -> AuthenticationProtocol:
        pass
