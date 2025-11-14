import time
from typing import Optional, Callable, Literal, cast, TypeAlias
from fastmcp import FastMCP
from ccpragents.domain.entities.pr_diff import PRDiff
from ccpragents.domain.usecases.pr_diff_usecases import GetPRDiffUseCase
from ccpragents.domain.services.pr_diff_service import PRDiffServiceInterface
from ccpragents.domain.services.settings import SettingsServiceInterface
from ccpragents.domain.services.cache import CacheServiceInterface
from ccpragents.domain.services.repository_cache import RepositoryCacheServiceInterface
from ccpragents.domain.services.logger import LoggerServiceInterface
from ccpragents.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from ccpragents.infrastructure.security.input_validator import InputValidator
from ccpragents.infrastructure.request_coalescing import RequestCoalescingService

from ccpragents.domain.exceptions import (
    InvalidURLError,
    InvalidRepositoryError,
    InvalidPRNumberError,
    InputSanitizationError,
    SuspiciousOperationError,
)

from .interfaces.protocols import (
    URLValidatorProtocol,
    RateLimiterProtocol,
    MetricsTrackerProtocol,
    PROperationHandlerProtocol,
    HealthMonitorProtocol,
    ServerConfigurationProtocol,
)


# Type alias for valid MCP transport modes
TransportMode: TypeAlias = Literal["stdio", "http", "sse", "streamable-http"]


class FastMCPServer:
    """FastMCP server for fetching GitHub PR diffs with detailed file change information.

    This server provides tools for retrieving pull request information:
    - get_pr_diff: Fetches PR diff information including file statistics

    Attributes:
        mcp: The FastMCP instance for tool registration and server management
        settings_service: Settings service for configuration
        logger: Logger for logging messages
    """

    def __init__(
        self,
        settings_service: SettingsServiceInterface,
        cache_service: CacheServiceInterface,
        repository_cache_service: RepositoryCacheServiceInterface,
        pr_diff_service: PRDiffServiceInterface,
        logger: LoggerServiceInterface,
        github_repository_class: Callable[[str, str, int], PRDiffRepositoryInterface],
        # Infrastructure dependencies injected via factory
        url_validator: URLValidatorProtocol,
        rate_limiter: RateLimiterProtocol,
        metrics_tracker: MetricsTrackerProtocol,
        pr_operation_handler: PROperationHandlerProtocol,
        health_monitor: HealthMonitorProtocol,
        server_configuration: ServerConfigurationProtocol,
        # Security and request coalescing services from infrastructure
        input_validator: Optional[InputValidator] = None,
        request_coalescing_service: Optional[RequestCoalescingService] = None,
    ):
        """Initialize the FastMCP server with dependency injection.

        Args:
            settings_service: Settings service instance implementing SettingsServiceInterface
            cache_service: Cache service instance implementing CacheServiceInterface
            repository_cache_service: Repository cache service instance implementing RepositoryCacheServiceInterface
            pr_diff_service: PR diff service instance implementing PRDiffServiceInterface
            logger: Logger instance implementing LoggerServiceInterface
            github_repository_class: GitHub repository class callable that creates PRDiffRepositoryInterface instances
            url_validator: URL validator component implementing URLValidatorProtocol
            rate_limiter: Rate limiter component implementing RateLimiterProtocol
            metrics_tracker: Metrics tracker component implementing MetricsTrackerProtocol
            pr_operation_handler: PR operation handler component implementing PROperationHandlerProtocol
            health_monitor: Health monitor component implementing HealthMonitorProtocol
            server_configuration: Server configuration component implementing ServerConfigurationProtocol
            input_validator: Optional input validator factory function (for backward compatibility)
            request_coalescing_service: Optional request coalescing service factory function (for backward compatibility)
        """
        self._settings_service = settings_service
        self._cache_service = cache_service
        self._repository_cache_service = repository_cache_service
        self._pr_diff_service = pr_diff_service
        self._logger = logger
        self._github_repository_class = github_repository_class

        # Infrastructure dependencies injected via factory
        self._url_validator = url_validator
        self._rate_limiter = rate_limiter
        self._metrics_tracker = metrics_tracker
        self._pr_operation_handler = pr_operation_handler
        self._health_monitor = health_monitor
        self._server_configuration = server_configuration

        # Initialize security validator - should be injected for Clean Architecture
        if input_validator is None:
            # Fallback to direct instantiation only for backward compatibility
            from ccpragents.infrastructure.security.input_validator import (
                InputValidator,
            )

            self._input_validator = InputValidator()
        else:
            self._input_validator = input_validator

        # Initialize request coalescing service - should be injected for Clean Architecture
        if request_coalescing_service is None:
            # Fallback to direct instantiation only for backward compatibility
            from ccpragents.infrastructure.request_coalescing import (
                get_request_coalescing_service,
            )

            self._request_coalescing = get_request_coalescing_service()
        else:
            self._request_coalescing = request_coalescing_service

        # Legacy fields for backward compatibility (will be removed in future versions)
        # Rate limiting configuration
        self._rate_limit_requests = 100  # Max requests per minute
        self._rate_limit_window = 60  # 60 second window
        self._request_timestamps: list[
            float
        ] = []  # Track request timestamps for rate limiting

        # Request tracking for structured logging
        self._request_counter = 0

        # Metrics tracking
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._start_time = time.time()

        # Initialize server configuration
        self._server_configuration.setup_logging()

        self._logger.info("Initializing FastMCP server", component="mcp_server")

        self.mcp = FastMCP(
            name="ccpragents",
            instructions=self._server_configuration.get_mcp_instructions(),
            version="0.1.3",
        )

        self._register_tools()

    def _parse_pr_url(self, pr_url: str) -> tuple[str, str, int]:
        """Parse GitHub PR URL to extract repository owner, name, and PR number.

        Args:
            pr_url: The GitHub pull request URL to parse

        Returns:
            tuple[str, str, int]: A tuple containing (repo_owner, repo_name, pr_number)

        Raises:
            InvalidURLError: If the URL format is invalid or contains invalid characters
            SuspiciousOperationError: If the URL contains suspicious patterns
        """
        return self._input_validator.validate_github_url(pr_url)

    def _check_rate_limit(self):
        """Check if the current request exceeds rate limits.

        Raises:
            RuntimeError: If rate limit is exceeded
        """
        if not self._rate_limiter.check_rate_limit("global"):
            rate_info = self._rate_limiter.get_rate_limit_info()
            raise RuntimeError(
                f"Rate limit exceeded. Maximum {rate_info['max_requests']} "
                f"requests per {rate_info['window_seconds']} seconds."
            )

        # Increment rate limit counter
        self._rate_limiter.increment_rate_limit("global")

    def _generate_request_id(self) -> str:
        """Generate a unique request ID for tracking purposes.

        Returns:
            str: Unique request ID in format REQ-{timestamp}-{counter}
        """
        return self._metrics_tracker.generate_request_id()

    def _get_health_status(self) -> dict:
        """Get health status and metrics for the MCP server.

        Returns:
            dict: Health status and metrics information
        """
        return self._health_monitor.check_health()

    def _register_tools(self):
        """Register FastMCP tools with the server instance.

        This method registers the get_pr_diff tool for PR diff information.
        """

        @self.mcp.tool()
        async def get_pr_diff(pr_url: str) -> PRDiff:
            """Get the diff content for a specific GitHub pull request.

            Automatic commit-based caching ensures fresh data is returned when the PR changes.

            Args:
                pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            """
            # Generate request ID for tracing
            request_id = self._generate_request_id()

            self._logger.info(
                "Processing get_pr_diff request",
                request_id=request_id,
                pr_url=pr_url,
            )

            # Track total requests (legacy + new metrics)
            self._total_requests += 1

            # Start tracking request time
            start_time = time.time()

            try:
                # Check rate limit
                self._check_rate_limit()

                # Validate input parameters using InputValidator
                if not pr_url:
                    raise InputSanitizationError("PR URL parameter is required")

                # Sanitize PR URL string (basic validation before detailed parsing)
                pr_url = self._input_validator.sanitize_string(pr_url, max_length=2000)

                # Parse and validate GitHub URL with security checks
                repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)

                # Create coalescing key
                coalesce_key = f"{repo_owner}/{repo_name}/pr/{pr_number}"

                # Define the actual fetch function
                async def fetch_pr_diff() -> PRDiff:
                    """Fetch PR diff - will be coalesced if multiple requests arrive."""
                    # Try to get repository from cache first
                    repository: Optional[PRDiffRepositoryInterface] = (
                        self._repository_cache_service.retrieve(
                            repo_owner, repo_name, pr_number
                        )
                    )

                    if repository is None:
                        # Create new repository instance
                        repository = self._github_repository_class(
                            repo_owner, repo_name, pr_number
                        )
                        self._logger.debug(
                            "Created new repository instance",
                            request_id=request_id,
                            repo_owner=repo_owner,
                            repo_name=repo_name,
                            pr_number=pr_number,
                        )
                    else:
                        self._logger.debug(
                            "Reusing cached repository instance",
                            request_id=request_id,
                            repo_owner=repo_owner,
                            repo_name=repo_name,
                            pr_number=pr_number,
                        )

                    use_case = GetPRDiffUseCase(
                        pr_diff_service=self._pr_diff_service,
                        cache_service=self._cache_service,
                    )
                    result = await use_case.execute(
                        repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number
                    )

                    # Handle case where use case returns None
                    if result is None:
                        self._logger.error(
                            "Use case returned None for PR diff",
                            request_id=request_id,
                            repo_owner=repo_owner,
                            repo_name=repo_name,
                            pr_number=pr_number,
                        )
                        raise ValueError("Failed to get PR diff - use case returned None")

                    # Cache the repository after it's been used
                    if hasattr(repository, "_initialized") and getattr(
                        repository, "_initialized", False
                    ):
                        cache_success = self._repository_cache_service.insert(
                            repository
                        )
                        if cache_success:
                            self._logger.debug(
                                "Cached repository instance after initialization",
                                request_id=request_id,
                                repo_owner=repo_owner,
                                repo_name=repo_name,
                                pr_number=pr_number,
                            )
                    return result

                # Coalesce the request - if multiple concurrent requests for same PR,
                # only one will actually fetch, others will wait and share the result
                pr_diff: PRDiff = await self._request_coalescing.coalesce(
                    coalesce_key, fetch_pr_diff
                )

                # Track successful request
                execution_time = time.time() - start_time
                self._metrics_tracker.track_request("get_pr_diff", True, execution_time)
                # Legacy metrics for backward compatibility
                self._successful_requests += 1

                self._logger.info("Successfully fetched PR diff")
                return pr_diff

            except (
                InvalidURLError,
                InvalidRepositoryError,
                InvalidPRNumberError,
                InputSanitizationError,
                SuspiciousOperationError,
            ) as e:
                # Track failed request
                execution_time = time.time() - start_time
                self._metrics_tracker.track_request(
                    "get_pr_diff", False, execution_time
                )
                # Legacy metrics for backward compatibility
                self._failed_requests += 1

                # Security validation errors - provide clear error messages
                self._logger.warning(
                    "Security validation error in PR diff request",
                    request_id=request_id,
                    pr_url=self._input_validator.sanitize_for_logging(pr_url)
                    if pr_url
                    else None,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise ValueError(f"Invalid request: {e}")

            except ValueError as e:
                # Track failed request
                execution_time = time.time() - start_time
                self._metrics_tracker.track_request(
                    "get_pr_diff", False, execution_time
                )
                # Legacy metrics for backward compatibility
                self._failed_requests += 1

                # Other validation errors - provide clear error messages
                self._logger.warning(
                    "Validation error in PR diff request",
                    request_id=request_id,
                    pr_url=self._input_validator.sanitize_for_logging(pr_url)
                    if pr_url
                    else None,
                    error=str(e),
                )
                raise ValueError(f"Invalid request: {e}")

            except Exception as e:
                # Track failed request
                execution_time = time.time() - start_time
                self._metrics_tracker.track_request(
                    "get_pr_diff", False, execution_time
                )
                # Legacy metrics for backward compatibility
                self._failed_requests += 1

                # GitHub API or other unexpected errors
                self._logger.error(
                    "Failed to fetch PR diff",
                    request_id=request_id,
                    pr_url=pr_url,
                    error=str(e),
                )
                # Re-raise with consistent error format
                raise RuntimeError(f"Failed to fetch PR diff: {e}")

        @self.mcp.tool()
        async def health():
            """Get server health status and metrics.

            Returns:
                dict: Health status and performance metrics
            """
            try:
                return self._get_health_status()
            except Exception as e:
                self._logger.error("Failed to get health status", error=str(e))
                return {"status": "unhealthy", "error": str(e)}

    def run(self):
        """Start the FastMCP server with configured transport and port.

        Configuration priority (highest to lowest):
        1. Environment variables (MCP_TRANSPORT, MCP_PORT, MCP_HOST, MCP_PATH)
        2. Settings file (settings.toml)
        3. Defaults (stdio transport, port 9102, host 127.0.0.1, path /mcp)

        Supported transports include "stdio", "http", "sse", and "streamable-http".
        """
        import os

        # Get MCP settings from environment variables first, then fall back to settings service
        transport_raw = os.getenv("MCP_TRANSPORT") or self._settings_service.get(
            "mcp.transport", "stdio"
        )
        port = int(os.getenv("MCP_PORT", "0")) or self._settings_service.get(
            "mcp.port", 9102
        )
        host = os.getenv("MCP_HOST") or self._settings_service.get(
            "mcp.host", "127.0.0.1"
        )
        path = os.getenv("MCP_PATH") or self._settings_service.get("mcp.path", "/mcp")

        # Validate and cast transport to the correct type
        valid_transports: tuple[TransportMode, ...] = (
            "stdio",
            "http",
            "sse",
            "streamable-http",
        )
        if transport_raw not in valid_transports:
            self._logger.warning(
                f"Invalid transport '{transport_raw}', defaulting to 'stdio'"
            )
            transport: TransportMode = "stdio"
        else:
            transport = cast(TransportMode, transport_raw)

        if transport == "stdio":
            self._logger.info("Running MCP server with stdio transport")
            self.mcp.run(transport="stdio")
        else:
            self._logger.info(
                f"Running MCP server with {transport} transport on {host}:{port}{path}"
            )
            self.mcp.run(transport=transport, port=port, host=host, path=path)
