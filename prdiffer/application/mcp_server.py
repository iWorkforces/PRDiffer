import os
from typing import Literal, TypeAlias, cast, Callable

from fastmcp import FastMCP
from prdiffer.version import __version__

from prdiffer.domain.services.settings import SettingsServiceInterface
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.repository_cache import RepositoryCacheServiceInterface
from prdiffer.domain.services.pr_diff_service import PRDiffServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.domain.interfaces.protocols import (
    RateLimiterProtocol,
    MetricsTrackerProtocol,
    PROperationHandlerProtocol,
    HealthMonitorProtocol,
    ServerConfigurationProtocol,
    AuthenticationProtocol,
)
from prdiffer.infrastructure.security.input_validator import InputValidator
from prdiffer.infrastructure.request_coalescing import RequestCoalescingService

from prdiffer.application.tool_registry import ToolRegistry
from prdiffer.application.webhook_handler import WebhookHandler
from prdiffer.application.health_endpoints import HealthEndpoints


# Type alias for valid MCP transport modes
TransportMode: TypeAlias = Literal["stdio", "http", "sse", "streamable-http"]


class FastMCPServer:
    """FastMCP server for fetching GitHub PR diffs with detailed file change information.

    This server provides tools for retrieving pull request information:
    - get_pr_diff: Fetches PR diff information including file statistics
    - approve_pr: Approves PR with compliment

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
        github_repository_class: Callable,
        # Infrastructure dependencies injected via factory
        rate_limiter: RateLimiterProtocol,
        metrics_tracker: MetricsTrackerProtocol,
        pr_operation_handler: PROperationHandlerProtocol,
        health_monitor: HealthMonitorProtocol,
        server_configuration: ServerConfigurationProtocol,
        authentication: AuthenticationProtocol | None = None,
        # Security and request coalescing services from infrastructure
        input_validator: InputValidator | None = None,
        request_coalescing_service: RequestCoalescingService | None = None,
    ):
        """Initialize the FastMCP server with dependency injection.

        Args:
            settings_service: Settings service instance implementing SettingsServiceInterface
            cache_service: Cache service instance implementing CacheServiceInterface
            repository_cache_service: Repository cache service instance implementing RepositoryCacheServiceInterface
            pr_diff_service: PR diff service instance implementing PRDiffServiceInterface
            logger: Logger instance implementing LoggerServiceInterface
            github_repository_class: GitHub repository class callable that creates PRDiffRepositoryInterface instances
            rate_limiter: Rate limiter component implementing RateLimiterProtocol
            metrics_tracker: Metrics tracker component implementing MetricsTrackerProtocol
            pr_operation_handler: PR operation handler component implementing PROperationHandlerProtocol
            health_monitor: Health monitor component implementing HealthMonitorProtocol
            server_configuration: Server configuration component implementing ServerConfigurationProtocol
            authentication: Authentication middleware component implementing AuthenticationProtocol
            input_validator: Optional input validator instance
            request_coalescing_service: Optional request coalescing service instance
        """
        self._settings_service = settings_service
        self._cache_service = cache_service
        self._repository_cache_service = repository_cache_service
        self._pr_diff_service = pr_diff_service
        self._logger = logger
        self._github_repository_class = github_repository_class

        # Infrastructure dependencies injected via factory
        self._rate_limiter = rate_limiter
        self._metrics_tracker = metrics_tracker
        self._pr_operation_handler = pr_operation_handler
        self._health_monitor = health_monitor
        self._server_configuration = server_configuration

        # Initialize authentication - use injected or create default
        if authentication is None:
            from prdiffer.application.components.authentication import (
                AuthenticationMiddleware,
            )

            self._authentication = AuthenticationMiddleware()
        else:
            self._authentication = authentication

        # Initialize security validator - use injected or create default
        if input_validator is None:
            from prdiffer.infrastructure.security.input_validator import (
                InputValidator,
            )

            self._input_validator = InputValidator()
        else:
            self._input_validator = input_validator

        # Initialize request coalescing service - use injected or create default
        if request_coalescing_service is None:
            from prdiffer.infrastructure.request_coalescing import (
                get_request_coalescing_service,
            )

            self._request_coalescing = get_request_coalescing_service()
        else:
            self._request_coalescing = request_coalescing_service

        # Initialize server configuration
        self._server_configuration.setup_logging()

        self._logger.info("Initializing FastMCP server", component="mcp_server")

        self.mcp = FastMCP(
            name="prdiffer",
            instructions=self._server_configuration.get_mcp_instructions(),
            version=__version__,
        )

        self._initialize_components()
        self._register_endpoints_and_tools()

    def _initialize_components(self):
        """Initialize component instances for tools, webhooks, and health endpoints."""

        # Initialize tool registry
        self._tool_registry = ToolRegistry(
            pr_diff_service=self._pr_diff_service,
            cache_service=self._cache_service,
            logger=self._logger,
            github_repository_class=self._github_repository_class,
            rate_limiter=self._rate_limiter,
            metrics_tracker=self._metrics_tracker,
            authentication=self._authentication,
            input_validator=self._input_validator,
            request_coalescing_service=self._request_coalescing,
        )

        # Initialize webhook handler
        self._webhook_handler = WebhookHandler(
            settings_service=self._settings_service,
            cache_service=self._cache_service,
            repository_cache_service=self._repository_cache_service,
            logger=self._logger,
            input_validator=self._input_validator,
        )

        # Initialize health endpoints
        self._health_endpoints = HealthEndpoints(
            health_monitor=self._health_monitor,
            metrics_tracker=self._metrics_tracker,
            cache_service=self._cache_service,
            repository_cache_service=self._repository_cache_service,
            authentication=self._authentication,
            request_coalescing=self._request_coalescing,
            logger=self._logger,
        )

    def _register_endpoints_and_tools(self):
        """Register all FastMCP tools and endpoints with the server instance."""

        # Register tools (get_pr_diff, approve_pr)
        self._tool_registry.register_tools(self.mcp)

        # Register health tool
        health_tool = self._health_endpoints.get_health_handler()
        self.mcp.tool()(health_tool)

        # Register metrics endpoint
        metrics_handler = self._health_endpoints.get_metrics_handler()
        self.mcp.custom_route("/metrics", methods=["GET"])(metrics_handler)

        # Register webhook endpoint
        webhook_handler_func = self._webhook_handler.get_webhook_handler()
        self.mcp.custom_route("/webhook", methods=["POST"])(webhook_handler_func)

    def run(self):
        """Start the FastMCP server with configured transport and port.

        Configuration priority (highest to lowest):
        1. Environment variables (MCP_TRANSPORT, MCP_PORT, MCP_HOST, MCP_PATH)
        2. Settings file (settings.toml)
        3. Defaults (http transport, port 9102, host 127.0.0.1, path /mcp)

        Supported transports include "stdio", "http", "sse", and "streamable-http".
        """

        # Get MCP settings from environment variables first, then fall back to settings service
        transport_raw = os.getenv("MCP_TRANSPORT") or self._settings_service.get(
            "mcp.transport", "http"
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
