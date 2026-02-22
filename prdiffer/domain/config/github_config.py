"""Centralized GitHub configuration dataclass.

This module provides a dataclass that centralizes all GitHub-related settings
in a single source of truth. Services receive a GitHubConfig object instead
of individual parameters.
"""

from dataclasses import dataclass, field

from .github_config_interface import GitHubConfigInterface


@dataclass(frozen=True)
class GitHubConfig(GitHubConfigInterface):
    """Centralized configuration for GitHub API interactions.

    This immutable dataclass contains all GitHub-related settings in one place,
    enabling:
    - Single source of truth for configuration
    - Easy parameter passing to services
    - Type-safe configuration access
    - Immutability for thread safety

    Attributes:
        rate_limit: Maximum API requests per hour
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for failed requests
        retry_delay: Base delay between retries in seconds

        retry_on_404: Whether to retry 404 errors
        retry_on_403: Whether to retry 403 errors (rate limiting)
        retry_on_500: Whether to retry 5xx server errors
        retry_log_level: Log level for retry attempts
        permanent_failure_log_level: Log level for permanent failures

        circuit_breaker_enabled: Enable circuit breaker pattern
        circuit_breaker_failure_threshold: Failures before opening circuit
        circuit_breaker_timeout: Seconds to keep circuit open
        adaptive_retry_enabled: Enable adaptive retry delays
        max_adaptive_delay: Maximum adaptive delay in seconds
        api_health_tracking: Track API health metrics
        context_aware_retry: Enable context-aware retry strategies

        ignore_patterns: File patterns to ignore (as tuple for hashability)
        valid_extensions: Valid file extensions (as tuple for hashability)

        diff_parallel_enabled: Enable parallel diff generation
        diff_parallel_threshold: Minimum files to trigger parallel processing
        diff_max_workers: Maximum worker threads for parallel processing
        diff_worker_timeout: Timeout per file in seconds

        max_files_allowed: Maximum files to process per PR
    """

    # Basic API settings
    rate_limit: int = 5000
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    # Smart retry settings
    retry_on_404: bool = False
    retry_on_403: bool = True
    retry_on_500: bool = True
    retry_log_level: str = "DEBUG"
    permanent_failure_log_level: str = "INFO"

    # Circuit breaker and adaptive retry
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    adaptive_retry_enabled: bool = True
    max_adaptive_delay: int = 30
    api_health_tracking: bool = True
    context_aware_retry: bool = True

    # File filtering patterns (tuples for hashability)
    ignore_patterns: tuple[str, ...] = field(default_factory=tuple)
    valid_extensions: tuple[str, ...] = field(default_factory=tuple)

    # Parallel diff processing
    diff_parallel_enabled: bool = True
    diff_parallel_threshold: int = 3
    diff_max_workers: int = 4
    diff_worker_timeout: float = 30.0

    # File processing limits
    max_files_allowed: int = 50

    # Diff processing thresholds (for chunked processing of large files)
    large_file_threshold: int = 5000
    chunk_size: int = 1000
    max_diff_size: int = 100000

    @classmethod
    def from_dict(cls, config: dict) -> "GitHubConfig":
        """Create GitHubConfig from a dictionary.

        Args:
            config: Dictionary containing configuration values

        Returns:
            GitHubConfig: New configuration instance
        """
        # Convert lists to tuples for hashability
        ignore_patterns = config.get("ignore_patterns", ())
        if isinstance(ignore_patterns, list):
            ignore_patterns = tuple(ignore_patterns)

        valid_extensions = config.get("valid_extensions", ())
        if isinstance(valid_extensions, list):
            valid_extensions = tuple(valid_extensions)

        return cls(
            rate_limit=config.get("rate_limit", 5000),
            timeout=config.get("timeout", 30),
            max_retries=config.get("max_retries", 3),
            retry_delay=float(config.get("retry_delay", 1.0)),
            retry_on_404=config.get("retry_on_404", False),
            retry_on_403=config.get("retry_on_403", True),
            retry_on_500=config.get("retry_on_500", True),
            retry_log_level=config.get("retry_log_level", "DEBUG"),
            permanent_failure_log_level=config.get("permanent_failure_log_level", "INFO"),
            circuit_breaker_enabled=config.get("circuit_breaker_enabled", True),
            circuit_breaker_failure_threshold=config.get("circuit_breaker_failure_threshold", 5),
            circuit_breaker_timeout=config.get("circuit_breaker_timeout", 60),
            adaptive_retry_enabled=config.get("adaptive_retry_enabled", True),
            max_adaptive_delay=config.get("max_adaptive_delay", 30),
            api_health_tracking=config.get("api_health_tracking", True),
            context_aware_retry=config.get("context_aware_retry", True),
            ignore_patterns=ignore_patterns,
            valid_extensions=valid_extensions,
            diff_parallel_enabled=config.get("diff_parallel_enabled", True),
            diff_parallel_threshold=config.get("diff_parallel_threshold", 3),
            diff_max_workers=config.get("diff_max_workers", 4),
            diff_worker_timeout=float(config.get("diff_worker_timeout", 30.0)),
            max_files_allowed=config.get("max_files_allowed", 50),
            # Diff processing thresholds
            large_file_threshold=config.get("large_file_threshold", 5000),
            chunk_size=config.get("chunk_size", 1000),
            max_diff_size=config.get("max_diff_size", 100000),
        )

    def to_dict(self) -> dict:
        """Convert configuration to dictionary.

        Returns:
            dict: Dictionary representation of configuration
        """
        return {
            "rate_limit": self.rate_limit,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "retry_on_404": self.retry_on_404,
            "retry_on_403": self.retry_on_403,
            "retry_on_500": self.retry_on_500,
            "retry_log_level": self.retry_log_level,
            "permanent_failure_log_level": self.permanent_failure_log_level,
            "circuit_breaker_enabled": self.circuit_breaker_enabled,
            "circuit_breaker_failure_threshold": self.circuit_breaker_failure_threshold,
            "circuit_breaker_timeout": self.circuit_breaker_timeout,
            "adaptive_retry_enabled": self.adaptive_retry_enabled,
            "max_adaptive_delay": self.max_adaptive_delay,
            "api_health_tracking": self.api_health_tracking,
            "context_aware_retry": self.context_aware_retry,
            "ignore_patterns": list(self.ignore_patterns),
            "valid_extensions": list(self.valid_extensions),
            "diff_parallel_enabled": self.diff_parallel_enabled,
            "diff_parallel_threshold": self.diff_parallel_threshold,
            "diff_max_workers": self.diff_max_workers,
            "diff_worker_timeout": self.diff_worker_timeout,
            "max_files_allowed": self.max_files_allowed,
            "large_file_threshold": self.large_file_threshold,
            "chunk_size": self.chunk_size,
            "max_diff_size": self.max_diff_size,
        }

    def with_overrides(self, **kwargs) -> "GitHubConfig":
        """Create new config with overridden values.

        Args:
            **kwargs: Values to override

        Returns:
            GitHubConfig: New configuration with overrides applied
        """
        current = self.to_dict()
        current.update(kwargs)
        return GitHubConfig.from_dict(current)

    @property
    def should_use_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be used."""
        return self.circuit_breaker_enabled

    @property
    def should_use_adaptive_retry(self) -> bool:
        """Check if adaptive retry should be used."""
        return self.adaptive_retry_enabled

    @property
    def should_track_api_health(self) -> bool:
        """Check if API health tracking should be used."""
        return self.api_health_tracking

    @property
    def should_use_parallel_diff(self) -> bool:
        """Check if parallel diff processing should be used."""
        return self.diff_parallel_enabled

    def should_ignore_file(self, filename: str) -> bool:
        """Check if a file should be ignored based on patterns.

        Args:
            filename: File path to check

        Returns:
            bool: True if file should be ignored
        """
        import fnmatch

        filename_lower = filename.lower()
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(filename_lower, pattern.lower()):
                return True
            # Also check if pattern is in the filename for directory patterns
            if pattern.endswith("/") and pattern[:-1].lower() in filename_lower:
                return True
        return False

    def has_valid_extension(self, filename: str) -> bool:
        """Check if a file has a valid extension.

        Args:
            filename: File path to check

        Returns:
            bool: True if file has valid extension (or no extensions configured)
        """
        if not self.valid_extensions:
            return True  # No restriction if no extensions configured

        for ext in self.valid_extensions:
            if filename.lower().endswith(ext.lower()):
                return True
        return False

    def should_process_file(self, filename: str) -> bool:
        """Check if a file should be processed.

        Args:
            filename: File path to check

        Returns:
            bool: True if file should be processed
        """
        return not self.should_ignore_file(filename) and self.has_valid_extension(filename)
