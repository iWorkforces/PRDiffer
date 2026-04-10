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
from prdiffer.domain.interfaces.input_validation import InputValidatorProtocol

from prdiffer.infrastructure.settings import get_settings_service
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.cache.service import get_cache_service
from prdiffer.infrastructure.cache.cache_repository import (
    get_repository_cache_service,
)
from prdiffer.infrastructure.github.client import GitHubAPIClient
from prdiffer.infrastructure.utils.diff_utils import DiffUtils, DiffProcessingConfig
from prdiffer.infrastructure.utils.pattern_matcher import PatternMatcher
from prdiffer.infrastructure.utils.retry.handler import RetryHandler
from prdiffer.infrastructure.github.diff_generator import (
    DiffGenerator,
    get_diff_generator,
)
from prdiffer.infrastructure.github.file_processor import FileProcessor

from prdiffer.infrastructure.services.pr_diff_service import GitHubPRDiffService


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
        settings_service = get_settings_service()
        github_settings = settings_service.get_github_settings()
        return GitHubAPIClient(
            max_retries=github_settings.get("max_retries", 3),
            retry_delay=github_settings.get("retry_delay", 1.0),
            timeout=github_settings.get("timeout", 30),
            retry_on_404=github_settings.get("retry_on_404", False),
            retry_on_403=github_settings.get("retry_on_403", True),
            retry_on_500=github_settings.get("retry_on_500", True),
            retry_log_level=github_settings.get("retry_log_level", "DEBUG"),
            permanent_failure_log_level=github_settings.get("permanent_failure_log_level", "INFO"),
            circuit_breaker_enabled=github_settings.get("circuit_breaker_enabled", True),
            circuit_breaker_failure_threshold=github_settings.get("circuit_breaker_failure_threshold", 5),
            circuit_breaker_timeout=github_settings.get("circuit_breaker_timeout", 60.0),
            adaptive_retry_enabled=github_settings.get("adaptive_retry_enabled", True),
            max_adaptive_delay=github_settings.get("max_adaptive_delay", 30),
            rate_limit_remaining_threshold=github_settings.get("rate_limit_remaining_threshold", 1),
            rate_limit_reset_buffer=github_settings.get("rate_limit_reset_buffer", 1.0),
            secondary_rate_limit_backoff=github_settings.get("secondary_rate_limit_backoff", 60.0),
            api_health_tracking=github_settings.get("api_health_tracking", True),
            context_aware_retry=github_settings.get("context_aware_retry", True),
            use_advanced_retry=github_settings.get("use_advanced_retry", True),
            max_concurrent=github_settings.get("max_concurrent", 4),
            file_content_cache_max_size=github_settings.get("file_content_cache_max_size", 1000),
            file_content_cache_ttl=github_settings.get("file_content_cache_ttl", 600),
        )

    def create_diff_service(self) -> DiffServiceInterface:
        """Create diff service instance."""
        settings_service = get_settings_service()
        # Read diff processing configuration from settings
        config = DiffProcessingConfig(
            large_file_threshold=settings_service.get("diff.large_file_threshold", 5000),
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
        from prdiffer.infrastructure.github.client import GitHubAPIClient

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
            parallel_fetch_threshold=settings_service.get("file_processing.parallel_fetch_threshold", 10),
            max_parallel_workers=settings_service.get("file_processing.concurrent_downloads", 3),
        )

        # Create diff generator
        diff_generator = get_diff_generator(
            diff_utils=diff_service,
            parallel_executor=None,  # Use sequential processing for simplicity
            parallel_enabled=False,
        )

        return GitHubPRDiffService(
            github_api_client=github_api_service if isinstance(github_api_service, GitHubAPIClient) else None,
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
            parallel_fetch_threshold=settings_service.get("file_processing.parallel_fetch_threshold", 10),
            max_parallel_workers=settings_service.get("file_processing.concurrent_downloads", 3),
        )

    def create_diff_generator(self) -> DiffGenerator:
        """Create diff generator instance."""
        diff_service = self.create_diff_service()

        return get_diff_generator(
            diff_utils=diff_service,
            parallel_executor=None,
            parallel_enabled=False,
        )

    def create_input_validator(self) -> InputValidatorProtocol:
        """Create input validator instance."""
        from prdiffer.infrastructure.security.input_validator import InputValidator

        return InputValidator()


def get_infrastructure_factory() -> InfrastructureFactoryInterface:
    """Get infrastructure factory instance."""
    return InfrastructureFactory()
