"""Concrete infrastructure factory implementation."""

from prdiffer.domain.factories.infrastructure_factory import (
    InfrastructureFactoryInterface,
)
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.services.pr_diff_service import PRDiffServiceInterface
from prdiffer.domain.services.settings import SettingsServiceInterface
from prdiffer.domain.services.repository_cache import RepositoryCacheServiceInterface
from prdiffer.domain.services.github_api import GitHubAPIServiceInterface
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

# Infrastructure implementations
from prdiffer.infrastructure.settings import get_settings_service
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.cache_service import get_cache_service
from prdiffer.infrastructure.repository_cache_service import (
    get_repository_cache_service,
)
from prdiffer.infrastructure.github.api_client import GitHubAPIClient
from prdiffer.infrastructure.utils.diff_utils import DiffUtils, DiffProcessingConfig
from prdiffer.infrastructure.utils.pattern_matcher import PatternMatcher
from prdiffer.infrastructure.utils.retry_handler import RetryHandler
from prdiffer.infrastructure.github.diff_generator import (
    DiffGenerator,
    get_diff_generator,
)
from prdiffer.infrastructure.github.file_processor import FileProcessor
from prdiffer.infrastructure.security.input_validator import InputValidator

# Infrastructure service implementations
from prdiffer.infrastructure.services.pr_diff_service import GitHubPRDiffService

# Application components
from prdiffer.application.components.rate_limiter import RateLimiter
from prdiffer.application.components.metrics_tracker import MetricsTracker
from prdiffer.application.components.pr_operation_handler import PROperationHandler
from prdiffer.application.components.health_monitor import HealthMonitor
from prdiffer.application.components.server_configuration import ServerConfiguration
from prdiffer.application.components.authentication import AuthenticationMiddleware


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
        settings_service = get_settings_service()
        # Read diff processing configuration from settings
        config = DiffProcessingConfig(
            large_file_threshold=settings_service.get(
                "diff.large_file_threshold", 5000
            ),
            chunk_size=settings_service.get("diff.chunk_size", 1000),
            max_diff_size=settings_service.get("diff.max_diff_size", 100000),
        )
        return DiffUtils(config=config.validate())

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
        settings_service = get_settings_service()
        github_api_service = self.create_github_api_service()
        diff_service = self.create_diff_service()
        pattern_matching_service = self.create_pattern_matching_service()
        logger_service = self.create_logger_service()

        # Create file processor
        file_processor = FileProcessor(
            github_api_service=github_api_service,
            pattern_matcher=pattern_matching_service,
            diff_utils=diff_service,
            parallel_fetch_threshold=settings_service.get(
                "file_processing.parallel_fetch_threshold", 10
            ),
            max_parallel_workers=settings_service.get(
                "file_processing.concurrent_downloads", 3
            ),
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
            logger=logger_service,
        )

    def create_file_processor(self) -> FileProcessor:
        """Create file processor instance."""
        settings_service = get_settings_service()
        github_api_service = self.create_github_api_service()
        diff_service = self.create_diff_service()
        pattern_matching_service = self.create_pattern_matching_service()

        return FileProcessor(
            github_api_service=github_api_service,
            pattern_matcher=pattern_matching_service,
            diff_utils=diff_service,
            parallel_fetch_threshold=settings_service.get(
                "file_processing.parallel_fetch_threshold", 10
            ),
            max_parallel_workers=settings_service.get(
                "file_processing.concurrent_downloads", 3
            ),
        )

    def create_diff_generator(self) -> DiffGenerator:
        """Create diff generator instance."""
        diff_service = self.create_diff_service()

        return get_diff_generator(
            diff_utils=diff_service,
            parallel_executor=None,
            parallel_enabled=False,
        )

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
            input_validator=InputValidator(),
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

    def create_authentication(
        self, logger: LoggerServiceInterface
    ) -> AuthenticationProtocol:
        """Create authentication middleware component."""
        return AuthenticationMiddleware(logger=logger)


def get_infrastructure_factory() -> InfrastructureFactoryInterface:
    """Get infrastructure factory instance."""
    return InfrastructureFactory()
