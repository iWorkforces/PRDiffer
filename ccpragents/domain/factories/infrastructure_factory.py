"""Infrastructure factory interface for Clean Architecture.

This module defines the InfrastructureFactoryInterface that provides
a clean abstraction for creating infrastructure services while maintaining
dependency inversion principle.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ccpragents.domain.services.cache import CacheServiceInterface
from ccpragents.domain.services.logger import LoggerServiceInterface
from ccpragents.domain.services.settings import SettingsServiceInterface
from ccpragents.domain.services.repository_cache import RepositoryCacheServiceInterface
from ccpragents.domain.services.github_api import GitHubAPIServiceInterface
from ccpragents.domain.services.diff import DiffServiceInterface
from ccpragents.domain.services.pattern_matching import PatternMatchingServiceInterface
from ccpragents.domain.services.retry import RetryServiceInterface

# Interface imports for infrastructure components
from ccpragents.application.interfaces.protocols import (
    URLValidatorProtocol,
    RateLimiterProtocol,
    MetricsTrackerProtocol,
    PROperationHandlerProtocol,
    HealthMonitorProtocol,
    ServerConfigurationProtocol,
)


class InfrastructureFactoryInterface(ABC):
    """Abstract factory for creating infrastructure services.

    This interface ensures that the application layer doesn't depend directly
    on infrastructure implementations, maintaining proper dependency inversion.
    """

    @abstractmethod
    def create_settings_service(self) -> SettingsServiceInterface:
        """Create settings service instance."""
        pass

    @abstractmethod
    def create_logger_service(self) -> LoggerServiceInterface:
        """Create logger service instance."""
        pass

    @abstractmethod
    def create_cache_service(self) -> CacheServiceInterface:
        """Create cache service instance."""
        pass

    @abstractmethod
    def create_repository_cache_service(self) -> RepositoryCacheServiceInterface:
        """Create repository cache service instance."""
        pass

    @abstractmethod
    def create_github_api_service(self) -> GitHubAPIServiceInterface:
        """Create GitHub API service instance."""
        pass

    @abstractmethod
    def create_diff_service(self) -> DiffServiceInterface:
        """Create diff service instance."""
        pass

    @abstractmethod
    def create_pattern_matching_service(self) -> PatternMatchingServiceInterface:
        """Create pattern matching service instance."""
        pass

    @abstractmethod
    def create_retry_service(self) -> RetryServiceInterface:
        """Create retry service instance."""
        pass

    # Application layer component factories
    @abstractmethod
    def create_url_validator(self, logger: LoggerServiceInterface) -> URLValidatorProtocol:
        """Create URL validator component."""
        pass

    @abstractmethod
    def create_rate_limiter(self, logger: LoggerServiceInterface) -> RateLimiterProtocol:
        """Create rate limiter component."""
        pass

    @abstractmethod
    def create_metrics_tracker(self, logger: LoggerServiceInterface) -> MetricsTrackerProtocol:
        """Create metrics tracker component."""
        pass

    @abstractmethod
    def create_pr_operation_handler(
        self,
        github_api_service: GitHubAPIServiceInterface,
        cache_service: CacheServiceInterface,
        repository_cache_service: RepositoryCacheServiceInterface,
        diff_service: DiffServiceInterface,
        pattern_matching_service: PatternMatchingServiceInterface,
        retry_service: RetryServiceInterface,
        logger: LoggerServiceInterface,
    ) -> PROperationHandlerProtocol:
        """Create PR operation handler component."""
        pass

    @abstractmethod
    def create_health_monitor(
        self,
        metrics_tracker: MetricsTrackerProtocol,
        rate_limiter: RateLimiterProtocol,
        logger: LoggerServiceInterface,
    ) -> HealthMonitorProtocol:
        """Create health monitor component."""
        pass

    @abstractmethod
    def create_server_configuration(
        self,
        settings_service: SettingsServiceInterface,
        logger: LoggerServiceInterface,
    ) -> ServerConfigurationProtocol:
        """Create server configuration component."""
        pass