"""Domain constants for PRDiffer.

This module contains all magic numbers and configuration constants used throughout
the codebase. Extracting these to a central location improves maintainability and
makes the codebase easier to understand and modify.
"""

from dataclasses import dataclass


class Limits:
    """Limits and maximum values for various inputs and operations."""

    # URL and input validation limits
    MAX_URL_LENGTH = 2000
    MAX_LOG_LENGTH = 200
    MAX_IDENTIFIER_LENGTH = 200
    MAX_PR_NUMBER = 1000000
    MAX_FILE_PATH_LENGTH = 500

    # GitHub API limits
    GITHUB_RATE_LIMIT_DEFAULT = 5000
    GITHUB_TIMEOUT_DEFAULT = 30
    GITHUB_MAX_RETRIES_DEFAULT = 3

    # Cache limits
    CACHE_MAX_SIZE_DEFAULT = 1000
    CACHE_TTL_DEFAULT = 600  # 10 minutes
    FILE_CONTENT_CACHE_MAX_SIZE = 1000
    FILE_CONTENT_CACHE_TTL = 600  # 10 minutes

    # Request coalescing limits
    MAX_WAITERS_DEFAULT = 100
    COALESCING_TIMEOUT_DEFAULT = 30.0

    # File processing limits
    MAX_FILES_ALLOWED_DEFAULT = 50

    # Circuit breaker limits
    CIRCUIT_BREAKER_FAILURE_THRESHOLD_DEFAULT = 5
    CIRCUIT_BREAKER_TIMEOUT_DEFAULT = 60.0

    # Parallel processing limits
    PARALLEL_DIFF_THRESHOLD_DEFAULT = 3
    DIFF_MAX_WORKERS_DEFAULT = 4
    DIFF_WORKER_TIMEOUT_DEFAULT = 30.0


class Thresholds:
    """Thresholds for change detection and classification."""

    # File change thresholds
    SIGNIFICANT_CHANGES = 50
    LARGE_CHANGES = 100
    LARGE_CHANGE_PERCENTAGE = 50
    VERY_LARGE_CHANGES = 500

    # Retry thresholds
    RETRY_DELAY_DEFAULT = 1.0
    MAX_ADAPTIVE_DELAY = 30.0
    LOCKOUT_DURATION_DEFAULT = 60  # seconds
    MAX_FAILURES_PER_MINUTE_DEFAULT = 5


class Defaults:
    """Default values for various configuration options."""

    # MCP server defaults
    MCP_TRANSPORT = "http"
    MCP_PORT = 9102
    MCP_HOST = "127.0.0.1"
    MCP_PATH = "/mcp"

    # Authentication defaults
    AUTH_ENABLED_DEFAULT = False  # Note: Should be True for production
    DEFAULT_CLIENT_ID = "anonymous"
    BEARER_PREFIX = "Bearer "
    API_KEY_HEADER = "X-API-Key"

    # Cache defaults
    USE_HASHED_KEYS = True
    HASH_ALGORITHM = "md5"  # Should be "sha256" for better security
    STORE_KEY_MAPPING = True

    # Logging defaults
    LOG_LEVEL = "INFO"
    DEBUG_LOG_LEVEL = "DEBUG"
    WARNING_LOG_LEVEL = "WARNING"
    ERROR_LOG_LEVEL = "ERROR"
    CRITICAL_LOG_LEVEL = "CRITICAL"

    # Retry log levels
    RETRY_LOG_LEVEL = "DEBUG"
    PERMANENT_FAILURE_LOG_LEVEL = "INFO"

    # Token validation
    MIN_TOKEN_LENGTH = 20
    MAX_TOKEN_LENGTH = 500
    HASH_PREFIX_LENGTH = 16  # Characters to show in logs


class Timeouts:
    """Timeout values for various operations."""

    # API timeouts
    GITHUB_API_TIMEOUT = 30
    FILE_FETCH_TIMEOUT = 30
    BATCH_OPERATION_TIMEOUT = 60

    # Request timeouts
    REQUEST_TIMEOUT_DEFAULT = 30
    REQUEST_TIMEOUT_MIN = 5
    REQUEST_TIMEOUT_MAX = 300


class RegularExpressions:
    """Regular expression patterns used throughout the codebase."""

    # GitHub URL patterns
    GITHUB_PR_URL_PATTERN = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    GITHUB_REPO_URL_PATTERN = r"https://github\.com/([^/]+)/([^/]+)"
    GITHUB_OWNER_PATTERN = r"^[a-zA-Z0-9]([a-zA-Z0-9-_]{0,38}[a-zA-Z0-9])?$"
    GITHUB_REPO_PATTERN = r"^[a-zA-Z0-9._-]+$"

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",  # Shell metacharacters
        r"\$\(",  # Command substitution
        r"`",  # Backtick substitution
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\.",  # Parent directory reference
        r"~",  # Home directory
    ]

    # SQL injection patterns
    SQL_INJECTION_KEYWORDS = [
        "union",
        "select",
        "insert",
        "update",
        "delete",
        "drop",
        "create",
        "alter",
        "exec",
        "execute",
    ]

    # Git ref validation
    GIT_REF_PATTERN = r"^[a-zA-Z0-9_\-./]+$"


@dataclass(frozen=True)
class GitHubConfig:
    """GitHub configuration dataclass.

    This immutable dataclass provides type-safe configuration for GitHub API operations.
    All values have sensible defaults that can be overridden when creating an instance.
    """

    # API settings
    rate_limit: int = Limits.GITHUB_RATE_LIMIT_DEFAULT
    timeout: int = Limits.GITHUB_TIMEOUT_DEFAULT
    max_retries: int = Limits.GITHUB_MAX_RETRIES_DEFAULT
    retry_delay: float = Thresholds.RETRY_DELAY_DEFAULT

    # Retry behavior
    retry_on_404: bool = False
    retry_on_403: bool = True
    retry_on_500: bool = True

    # Circuit breaker
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = (
        Limits.CIRCUIT_BREAKER_FAILURE_THRESHOLD_DEFAULT
    )
    circuit_breaker_timeout: float = Limits.CIRCUIT_BREAKER_TIMEOUT_DEFAULT

    # Adaptive retry
    adaptive_retry_enabled: bool = True
    max_adaptive_delay: float = Thresholds.MAX_ADAPTIVE_DELAY
    api_health_tracking: bool = True
    context_aware_retry: bool = True

    # Parallel processing
    diff_parallel_enabled: bool = True
    diff_parallel_threshold: int = Limits.PARALLEL_DIFF_THRESHOLD_DEFAULT
    diff_max_workers: int = Limits.DIFF_MAX_WORKERS_DEFAULT
    diff_worker_timeout: float = Limits.DIFF_WORKER_TIMEOUT_DEFAULT

    # File filtering
    max_files_allowed: int = Limits.MAX_FILES_ALLOWED_DEFAULT
    ignore_patterns: tuple = ()  # Set via settings
    valid_extensions: tuple = ()  # Set via settings


# Export commonly used constants for convenience
__all__ = [
    "Limits",
    "Thresholds",
    "Defaults",
    "Timeouts",
    "RegularExpressions",
    "GitHubConfig",
]
