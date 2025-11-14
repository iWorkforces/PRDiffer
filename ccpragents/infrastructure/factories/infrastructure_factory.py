"""Concrete infrastructure factory implementation."""

from ccpragents.domain.factories.infrastructure_factory import (
    InfrastructureFactoryInterface,
)
from ccpragents.domain.services.cache import CacheServiceInterface
from ccpragents.domain.services.file_processing_service import (
    FileProcessingServiceInterface,
)
from ccpragents.domain.services.logger import LoggerServiceInterface
from ccpragents.domain.services.pr_diff_service import PRDiffServiceInterface
from ccpragents.domain.services.settings import SettingsServiceInterface
from ccpragents.domain.services.repository_cache import RepositoryCacheServiceInterface
from ccpragents.domain.services.github_api import GitHubAPIServiceInterface
from ccpragents.domain.services.diff import DiffServiceInterface
from ccpragents.domain.services.pattern_matching import PatternMatchingServiceInterface
from ccpragents.domain.services.retry import RetryServiceInterface

from ccpragents.application.interfaces.protocols import (
    URLValidatorProtocol,
    RateLimiterProtocol,
    MetricsTrackerProtocol,
    PROperationHandlerProtocol,
    HealthMonitorProtocol,
    ServerConfigurationProtocol,
)

# Infrastructure implementations
from ccpragents.infrastructure.settings import get_settings_service
from ccpragents.infrastructure.logging.console_logger import get_logger
from ccpragents.infrastructure.cache_service import get_cache_service
from ccpragents.infrastructure.repository_cache_service import (
    get_repository_cache_service,
)
from ccpragents.infrastructure.github.api_client import GitHubAPIClient
from ccpragents.infrastructure.utils.diff_utils import DiffUtils
from ccpragents.infrastructure.utils.pattern_matcher import PatternMatcher
from ccpragents.infrastructure.utils.retry_handler import RetryHandler
from ccpragents.infrastructure.github.diff_generator import (
    DiffGenerator,
    get_diff_generator,
)
from ccpragents.infrastructure.github.file_processor import FileProcessor

# Infrastructure service implementations
from ccpragents.infrastructure.services.pr_diff_service import GitHubPRDiffService
from ccpragents.infrastructure.services.file_processing_service import (
    GitHubFileProcessingService,
)

# Application components
from ccpragents.application.components.url_validator import URLValidator
from ccpragents.application.components.rate_limiter import RateLimiter
from ccpragents.application.components.metrics_tracker import MetricsTracker
from ccpragents.application.components.pr_operation_handler import PROperationHandler
from ccpragents.application.components.health_monitor import HealthMonitor
from ccpragents.application.components.server_configuration import ServerConfiguration


class InfrastructureFactory(InfrastructureFactoryInterface):
    """Concrete implementation of infrastructure factory."""

    def create_settings_service(self) -> SettingsServiceInterface:
        """Create settings service instance."""
        return get_settings_service()

    def create_logger_service(self) -> LoggerServiceInterface:
        """Create logger service instance."""
        return get_logger()

    def create_cache_service(self) -> CacheServiceInterface:
        """Create cache service instance."""
        return get_cache_service()

    def create_repository_cache_service(self) -> RepositoryCacheServiceInterface:
        """Create repository cache service instance."""
        return get_repository_cache_service()

    def create_github_api_service(self) -> GitHubAPIServiceInterface:
        """Create GitHub API service instance."""
        return GitHubAPIClient()

    def create_diff_service(self) -> DiffServiceInterface:
        """Create diff service instance."""
        return DiffUtils()

    def create_pattern_matching_service(self) -> PatternMatchingServiceInterface:
        """Create pattern matching service instance."""
        settings_service = get_settings_service()
        github_settings = settings_service.get_github_settings()

        ignore_patterns = github_settings.get("ignore_patterns", [])
        valid_extensions = github_settings.get("valid_extensions", [])

        return PatternMatcher(
            ignore_patterns=list(ignore_patterns) if ignore_patterns else [],
            valid_extensions=list(valid_extensions) if valid_extensions else [],
        )

    def create_retry_service(self) -> RetryServiceInterface:
        """Create retry service instance."""
        return RetryHandler()

    def create_pr_diff_service(self) -> PRDiffServiceInterface:
        """Create PR diff service instance."""
        # Create dependencies
        github_api_service = self.create_github_api_service()
        diff_service = self.create_diff_service()
        pattern_matching_service = self.create_pattern_matching_service()

        # Create file processor
        file_processor = FileProcessor(
            github_api_service=github_api_service,
            pattern_matcher=pattern_matching_service,
            diff_utils=diff_service,
        )

        # Create diff generator
        diff_generator = get_diff_generator(
            diff_utils=diff_service,
            parallel_executor=None,  # Use sequential processing for simplicity
            parallel_enabled=False,
        )

        # Create PR diff service with dependencies
        return GitHubPRDiffService(
            github_api_client=github_api_service,
            diff_generator=diff_generator,
            file_processor=file_processor,
        )

    def create_file_processor(self) -> FileProcessor:
        """Create file processor instance."""
        github_api_service = self.create_github_api_service()
        diff_service = self.create_diff_service()
        pattern_matching_service = self.create_pattern_matching_service()

        return FileProcessor(
            github_api_service=github_api_service,
            pattern_matcher=pattern_matching_service,
            diff_utils=diff_service,
        )

    def create_diff_generator(self) -> DiffGenerator:
        """Create diff generator instance."""
        diff_service = self.create_diff_service()

        return get_diff_generator(
            diff_utils=diff_service,
            parallel_executor=None,
            parallel_enabled=False,
        )

    def create_file_processing_service(self) -> FileProcessingServiceInterface:
        """Create file processing service instance."""
        logger = self.create_logger_service()
        return GitHubFileProcessingService(logger=logger)

    def create_url_validator(
        self, logger: LoggerServiceInterface
    ) -> URLValidatorProtocol:
        """Create URL validator component."""
        return URLValidator()

    def create_rate_limiter(
        self, logger: LoggerServiceInterface
    ) -> RateLimiterProtocol:
        """Create rate limiter component."""
        return RateLimiter(logger=logger)

    def create_metrics_tracker(
        self, logger: LoggerServiceInterface
    ) -> MetricsTrackerProtocol:
        """Create metrics tracker component."""
        return MetricsTracker(logger=logger)

    def create_pr_operation_handler(
        self,
        github_repository_class,
        cache_service: CacheServiceInterface,
        repository_cache_service: RepositoryCacheServiceInterface,
        diff_service: DiffServiceInterface,
        pattern_matching_service: PatternMatchingServiceInterface,
        retry_service: RetryServiceInterface,
        logger: LoggerServiceInterface,
    ) -> PROperationHandlerProtocol:
        """Create PR operation handler component."""
        return PROperationHandler(
            github_repository_class=github_repository_class,
            cache_service=cache_service,
            repository_cache_service=repository_cache_service,
            logger=logger,
        )

    def create_health_monitor(
        self,
        metrics_tracker: MetricsTrackerProtocol,
        rate_limiter: RateLimiterProtocol,
        logger: LoggerServiceInterface,
    ) -> HealthMonitorProtocol:
        """Create health monitor component."""
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
        """Create server configuration component."""
        return ServerConfiguration(
            settings_service=settings_service,
            logger=logger,
        )


def get_infrastructure_factory() -> InfrastructureFactoryInterface:
    """Get infrastructure factory instance."""
    return InfrastructureFactory()
