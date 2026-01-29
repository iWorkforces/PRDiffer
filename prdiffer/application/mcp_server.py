import time
import hashlib
import hmac
import json
from typing import Optional, Callable, Literal, TypeAlias, NoReturn, cast
from fastmcp import FastMCP
from starlette.responses import JSONResponse
from prdiffer.version import __version__
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.usecases.pr_diff_usecases import GetPRDiffUseCase
from prdiffer.domain.services.pr_diff_service import PRDiffServiceInterface
from prdiffer.domain.services.settings import SettingsServiceInterface
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.repository_cache import RepositoryCacheServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface, LogLevel
from prdiffer.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface
from prdiffer.infrastructure.security.input_validator import InputValidator
from prdiffer.infrastructure.request_coalescing import RequestCoalescingService

from prdiffer.domain.exceptions import (
    InvalidURLError,
    InvalidRepositoryError,
    InvalidPRNumberError,
    InputSanitizationError,
    SuspiciousOperationError,
)

from prdiffer.domain.interfaces.protocols import (
    RateLimiterProtocol,
    MetricsTrackerProtocol,
    PROperationHandlerProtocol,
    HealthMonitorProtocol,
    ServerConfigurationProtocol,
    AuthenticationProtocol,
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
        rate_limiter: RateLimiterProtocol,
        metrics_tracker: MetricsTrackerProtocol,
        pr_operation_handler: PROperationHandlerProtocol,
        health_monitor: HealthMonitorProtocol,
        server_configuration: ServerConfigurationProtocol,
        authentication: Optional[AuthenticationProtocol] = None,
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

        self._register_tools()

    def _create_safe_error_message(self, exception: Exception) -> str:
        """Create a safe error message that doesn't expose internal details.

        This method maps known exception types to generic, user-friendly messages
        to prevent leaking sensitive system information in error responses.

        Args:
            exception: The exception to create a safe message for

        Returns:
            str: A safe error message suitable for external consumption
        """
        # Map known exception types to safe, generic messages
        safe_messages = {
            # GitHub API exceptions
            "GithubException": "GitHub API error occurred",
            "RateLimitExceededException": "API rate limit exceeded. Please try again later",
            "UnknownObjectException": "Repository or PR not found",
            "BadCredentialsException": "GitHub authentication failed",
            "TwoFactorException": "Two-factor authentication required",
            # Security validation exceptions
            "InvalidURLError": "Invalid GitHub PR URL format",
            "InvalidRepositoryError": "Invalid repository identifier",
            "InvalidPRNumberError": "Invalid pull request number",
            "InputSanitizationError": "Invalid input parameters",
            "SuspiciousOperationError": "Request contains suspicious patterns",
            # Network/connection exceptions
            "ConnectionError": "Connection to GitHub failed",
            "TimeoutError": "Request timed out",
            "SSLError": "Secure connection failed",
            # Generic Python exceptions
            "ValueError": "Invalid input value",
            "TypeError": "Invalid input type",
            "KeyError": "Missing required field",
            "AttributeError": "Configuration error",
        }

        exception_type = type(exception).__name__

        # Return mapped message if available, otherwise generic message
        if exception_type in safe_messages:
            return safe_messages[exception_type]

        # For unknown exceptions, return a generic message
        # Never expose the actual exception message which might contain sensitive info
        return "Request processing failed"

    def _parse_pr_url(self, pr_url: str) -> tuple[str, str, int]:
        """Parse GitHub PR URL to extract repository owner, name, and PR number.

        Args:
            pr_url: The GitHub pull request URL to parse

        Returns:
            tuple[str, str, int]: A tuple containing (repo_owner, repo_name, pr_number)

        Raises:
            InvalidURLError: If the URL format is invalid, contains invalid characters, or is empty/whitespace-only
            SuspiciousOperationError: If the URL contains suspicious patterns
        """
        # Validate input is not None or empty before processing
        if pr_url is None:
            raise InvalidURLError("PR URL cannot be None")

        if not isinstance(pr_url, str):
            raise InvalidURLError(
                f"PR URL must be a string, got {type(pr_url).__name__}"
            )

        pr_url_stripped = pr_url.strip()
        if not pr_url_stripped:
            raise InvalidURLError("PR URL cannot be empty or whitespace-only")

        # Delegate to input validator for full validation
        return self._input_validator.validate_github_url(pr_url_stripped)

    def _check_rate_limit(self, client_id: str = "global"):
        """Check if the current request exceeds rate limits.

        Args:
            client_id: Unique identifier for rate limiting (e.g., API key hash or IP)

        Raises:
            RuntimeError: If rate limit is exceeded
        """
        if not self._rate_limiter.check_rate_limit(client_id):
            rate_info = self._rate_limiter.get_rate_limit_info()
            raise RuntimeError(
                f"Rate limit exceeded for client '{client_id}'. Maximum {rate_info['max_requests']} "
                f"requests per {rate_info['window_seconds']} seconds."
            )

        # Increment rate limit counter
        self._rate_limiter.increment_rate_limit(client_id)

    def _generate_request_id(self) -> str:
        """Generate a unique request ID for tracking purposes.

        Returns:
            str: Unique request ID in format REQ-{timestamp}-{counter}
        """
        return self._metrics_tracker.generate_request_id()

    async def _get_health_status(self) -> dict:
        """Get health status and metrics for the MCP server.

        Returns:
            dict: Health status and metrics information
        """
        health_status = self._health_monitor.check_health()
        # Add authentication status
        health_status["authentication"] = self._authentication.get_status()
        health_status["cache"] = self._cache_service.get_stats()
        health_status["repository_cache"] = self._repository_cache_service.stats()
        health_status["request_coalescing"] = await self._request_coalescing.get_stats()
        return health_status

    async def _authenticate_request(
        self, request_id: str, start_time: float, api_key: Optional[str]
    ) -> Optional[str]:
        """Authenticate the incoming request using API key if authentication is enabled.

        Args:
            request_id: Unique request identifier for tracing
            start_time: Request start time for metrics tracking
            api_key: Optional API key for authentication

        Returns:
            Optional[str]: Client ID if authentication successful, None for anonymous

        Raises:
            ValueError: If authentication fails or rate limit is exceeded
        """
        try:
            is_authenticated, client_id = self._authentication.authenticate(api_key)
        except RuntimeError as e:
            execution_time = time.time() - start_time
            self._metrics_tracker.track_request("get_pr_diff", False, execution_time)
            self._logger.warning(
                "Authentication rate limited",
                request_id=request_id,
                error=str(e),
            )
            raise ValueError(str(e))

        if not is_authenticated:
            self._logger.warning("Authentication failed", request_id=request_id)
            raise ValueError(
                "Authentication failed. Please provide a valid API key via the 'api_key' parameter."
            )

        return client_id

    def _validate_and_sanitize_params(self, pr_url: str) -> tuple[str, str, int]:
        """Validate and sanitize the input PR URL parameter.

        Args:
            pr_url: The GitHub PR URL to validate

        Returns:
            tuple[str, str, int]: Parsed (repo_owner, repo_name, pr_number)

        Raises:
            InputSanitizationError: If PR URL parameter is missing or invalid
            InvalidURLError: If URL format is invalid or contains suspicious patterns
        """
        if not pr_url:
            raise InputSanitizationError("PR URL parameter is required")

        # Sanitize PR URL string (basic validation before detailed parsing)
        pr_url = self._input_validator.sanitize_string(pr_url, max_length=2000)

        # Parse and validate GitHub URL with security checks
        return self._parse_pr_url(pr_url)

    async def _execute_use_case_with_coalescing(
        self, request_id: str, repo_owner: str, repo_name: str, pr_number: int
    ) -> PRDiff:
        """Execute the PR diff use case with request coalescing for concurrent requests.

        Args:
            request_id: Unique request identifier for tracing
            repo_owner: Repository owner name
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            PRDiff: The PR diff result

        Raises:
            ValueError: If use case returns None
        """
        # Create coalescing key
        coalesce_key = f"{repo_owner}/{repo_name}/pr/{pr_number}"

        # Define the actual fetch function
        async def fetch_pr_diff() -> PRDiff:
            """Fetch PR diff - will be coalesced if multiple requests arrive."""
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

            return result

        # Coalesce the request - if multiple concurrent requests for same PR,
        # only one will actually fetch, others will wait and share the result
        return await self._request_coalescing.coalesce(coalesce_key, fetch_pr_diff)

    def _log_metrics_and_return_success(
        self, start_time: float, pr_diff: PRDiff
    ) -> PRDiff:
        """Log successful request metrics and return PR diff result.

        Args:
            start_time: Request start time
            pr_diff: The PR diff result to return

        Returns:
            PRDiff: The unchanged PR diff result
        """
        execution_time = time.time() - start_time
        self._metrics_tracker.track_request("get_pr_diff", True, execution_time)

        diff_size = len(pr_diff.files)
        diff_hash = hashlib.md5(str(pr_diff.files).encode()).hexdigest()[:8]

        self._logger.info(
            f"Successfully fetched PR diff - files: {diff_size}, hash: {diff_hash}..."
        )

        if self._logger.should_log(LogLevel.DEBUG):
            sanitized_preview = self._input_validator.sanitize_for_logging(
                f"Files: {len(pr_diff.files)}, preview: {pr_diff.files[:2] if pr_diff.files else []}",
                max_length=500,
            )
            self._logger.debug(
                f"PR diff content preview (sanitized): {sanitized_preview}"
            )

        self._logger.info(
            "PR Diff (Pretty JSON):\n" + json.dumps(pr_diff.model_dump(), indent=2)
        )

        return pr_diff

    def _handle_security_exception(
        self, exception: Exception, start_time: float, request_id: str, pr_url: str
    ) -> NoReturn:
        """Handle security validation exceptions with appropriate logging and re-raising.

        Args:
            exception: The security exception to handle
            start_time: Request start time for metrics
            request_id: Unique request identifier
            pr_url: The PR URL (sanitized for logging)

        Raises:
            ValueError: Always raises with safe error message
        """
        execution_time = time.time() - start_time
        self._metrics_tracker.track_request("get_pr_diff", False, execution_time)

        self._logger.warning(
            "Security validation error in PR diff request",
            request_id=request_id,
            pr_url=self._input_validator.sanitize_for_logging(pr_url)
            if pr_url
            else None,
            error=str(exception),
            error_type=type(exception).__name__,
        )

        safe_message = self._create_safe_error_message(exception)
        raise ValueError(f"Invalid request: {safe_message}")

    def _handle_validation_exception(
        self, exception: Exception, start_time: float, request_id: str, pr_url: str
    ) -> NoReturn:
        """Handle general validation exceptions with appropriate logging and re-raising.

        Args:
            exception: The validation exception to handle
            start_time: Request start time for metrics
            request_id: Unique request identifier
            pr_url: The PR URL (sanitized for logging)

        Raises:
            ValueError: Always raises with safe error message
        """
        execution_time = time.time() - start_time
        self._metrics_tracker.track_request("get_pr_diff", False, execution_time)

        self._logger.warning(
            "Validation error in PR diff request",
            request_id=request_id,
            pr_url=self._input_validator.sanitize_for_logging(pr_url)
            if pr_url
            else None,
            error=str(exception),
        )

        safe_message = self._create_safe_error_message(exception)
        raise ValueError(f"Invalid request: {safe_message}")

    def _handle_runtime_exception(
        self, exception: Exception, start_time: float, request_id: str, pr_url: str
    ) -> NoReturn:
        """Handle runtime exceptions (GitHub API, network errors) with logging and re-raising.

        Args:
            exception: The runtime exception to handle
            start_time: Request start time for metrics
            request_id: Unique request identifier
            pr_url: The PR URL (sanitized for logging)

        Raises:
            RuntimeError: Always raises with safe error message
        """
        execution_time = time.time() - start_time
        self._metrics_tracker.track_request("get_pr_diff", False, execution_time)

        self._logger.error(
            "Failed to fetch PR diff",
            request_id=request_id,
            pr_url=self._input_validator.sanitize_for_logging(pr_url)
            if pr_url
            else None,
            error=str(exception),
            error_type=type(exception).__name__,
        )

        safe_message = self._create_safe_error_message(exception)
        raise RuntimeError(f"Failed to fetch PR diff: {safe_message}")

    async def webhook_invalidate_cache(
        self, payload: dict, signature: str, github_event: str
    ) -> dict:
        """Handle webhook events for cache invalidation with HMAC verification.

        Args:
            payload: Webhook payload from GitHub
            signature: HMAC signature header value
            github_event: GitHub event type (push, pull_request, etc.)

        Returns:
            dict: Response indicating success or failure

        Raises:
            ValueError: If signature verification fails or payload is invalid
        """
        webhook_secret = self._settings_service.get("github.webhook.secret", default="")

        if not webhook_secret:
            self._logger.warning(
                "Webhook received but no secret configured",
                github_event=github_event,
            )
            return {"status": "error", "message": "Webhook secret not configured"}

        if github_event not in ["pull_request", "push"]:
            self._logger.warning(
                "Unsupported webhook event type",
                github_event=github_event,
            )
            return {"status": "error", "message": "Unsupported event type"}

        repository = payload.get("repository", {})
        repository_full_name = repository.get("full_name", "")
        number = payload.get("number")
        action = payload.get("action")
        cache_key = None

        if not repository_full_name:
            self._logger.warning(
                "Webhook payload missing repository information",
                github_event=github_event,
            )
            return {"status": "error", "message": "Missing repository info"}

        import json

        payload_bytes = json.dumps(payload).encode("utf-8")

        expected_signature = f"sha1={hmac.new(webhook_secret.encode(), payload_bytes, 'sha1').hexdigest()}"

        if not hmac.compare_digest(expected_signature.encode(), signature.encode()):
            self._logger.warning(
                "Invalid webhook signature",
                github_event=github_event,
            )
            return {"status": "error", "message": "Invalid signature"}

        if github_event == "pull_request":
            if action in ["opened", "synchronize", "reopened"]:
                cache_key = f"{repository_full_name}/pr/{number}"
                self._logger.info(
                    "Invalidating cache on PR updated",
                    cache_key=cache_key,
                    github_event=github_event,
                )
                self._repository_cache_service.invalidate(cache_key)
        elif github_event == "push":
            cache_key = repository_full_name
            self._logger.info(
                "Invalidating cache on push",
                cache_key=cache_key,
                github_event=github_event,
            )
            self._repository_cache_service.invalidate(cache_key)
            self._cache_service.invalidate(repository_full_name)

        self._logger.info(
            "Webhook processed successfully",
            github_event=github_event,
            cache_key=cache_key if cache_key else "N/A",
        )

        return {"status": "success", "message": "Cache invalidated"}

    def _register_tools(self):
        """Register FastMCP tools with the server instance.

        This method registers the get_pr_diff tool for PR diff information.
        """

        @self.mcp.tool()
        async def get_pr_diff(pr_url: str, api_key: Optional[str] = None) -> PRDiff:
            """Get the structured file-level diff content for a specific GitHub pull request.

            Returns per-file diff information including:
            - File paths
            - Edit status (added, modified, deleted, renamed, unknown)
            - Line statistics (additions, deletions)
            - Full patch content for each file

            Args:
                pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                api_key: Optional API key for authentication (required if auth enabled)

            Raises:
                ValueError: If authentication fails or URL is invalid
                RuntimeError: If rate limit is exceeded or API request fails

            Note:
                Breaking Change: Response now returns structured files array instead of concatenated diff_content string.
                Automatic commit-based caching ensures fresh data is returned when PR changes.
            """

            request_id = self._generate_request_id()
            start_time = time.time()

            self._logger.info(
                "Processing get_pr_diff request",
                request_id=request_id,
                pr_url=pr_url,
            )

            # Authenticate request
            client_id = await self._authenticate_request(
                request_id, start_time, api_key
            )

            # Use authenticated client_id for rate limiting
            # Fallback to "anonymous" if no client_id provided
            rate_limit_client_id = client_id or "anonymous"

            try:
                # Check rate limit with client-specific identifier
                self._check_rate_limit(rate_limit_client_id)

                # Validate and sanitize input parameters
                repo_owner, repo_name, pr_number = self._validate_and_sanitize_params(
                    pr_url
                )

                # Execute use case with request coalescing
                pr_diff = await self._execute_use_case_with_coalescing(
                    request_id, repo_owner, repo_name, pr_number
                )

                # Track successful request and return
                return self._log_metrics_and_return_success(start_time, pr_diff)

            except (
                InvalidURLError,
                InvalidRepositoryError,
                InvalidPRNumberError,
                InputSanitizationError,
                SuspiciousOperationError,
            ) as e:
                self._handle_security_exception(e, start_time, request_id, pr_url)

            except ValueError as e:
                self._handle_validation_exception(e, start_time, request_id, pr_url)

            except (
                RuntimeError,
                KeyError,
                AttributeError,
                TypeError,
                ConnectionError,
            ) as e:
                self._handle_runtime_exception(e, start_time, request_id, pr_url)

        @self.mcp.tool()
        async def health():
            """Get server health status and metrics.

            Returns:
                dict: Health status and performance metrics
            """
            try:
                return await self._get_health_status()
            except (RuntimeError, KeyError, AttributeError) as e:
                # Log full error internally for debugging
                self._logger.error(
                    "Failed to get health status",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Return safe error message that doesn't expose internals
                safe_message = self._create_safe_error_message(e)
                return {"status": "unhealthy", "error": safe_message}

        @self.mcp.custom_route("/webhook", methods=["POST"])
        async def webhook_handler(request):
            """Handle GitHub webhook events for cache invalidation.

            GitHub sends webhook events to this endpoint, which triggers
            cache invalidation for affected repositories and PRs.

            Args:
                request: FastAPI Request object containing webhook payload and headers

            Returns:
                JSONResponse with status indicating success or failure
            """
            import json

            try:
                signature = request.headers.get("X-Hub-Signature", "")
                github_event = request.headers.get("X-GitHub-Event", "")

                payload = await request.json()

                result = await self.webhook_invalidate_cache(
                    payload, signature, github_event
                )

                return JSONResponse(result, status_code=200)
            except json.JSONDecodeError as e:
                self._logger.error(
                    "Failed to parse webhook payload",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return JSONResponse(
                    {"status": "error", "message": "Invalid JSON payload"},
                    status_code=400,
                )
            except Exception as e:
                self._logger.error(
                    "Webhook handler error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return JSONResponse(
                    {"status": "error", "message": "Internal server error"},
                    status_code=500,
                )

        @self.mcp.custom_route("/metrics", methods=["GET"])
        async def metrics_handler(request):
            try:
                metrics = self._metrics_tracker.get_metrics_summary()
                return JSONResponse(metrics)
            except (RuntimeError, KeyError, AttributeError) as e:
                self._logger.error(
                    "Failed to get metrics",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return JSONResponse(
                    {
                        "server": "prdiffer",
                        "error": "Failed to get metrics",
                        "message": "Internal server error",
                    },
                    status_code=500,
                )

        @self.mcp.tool()
        async def approve_pr(
            pr_url: str, compliment: str, api_key: Optional[str] = None
        ) -> str:
            """Approve a GitHub PR with a compliment comment.

            This method approves a pull request with a provided compliment text.

            Args:
                pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                compliment: The compliment text to include in the approval review
                api_key: Optional API key for authentication (required if authentication is enabled)

            Returns:
                str: Success message indicating PR was approved

            Raises:
                ValueError: If authentication fails, URL is invalid, or compliment is missing
                RuntimeError: If rate limit is exceeded or API request fails
            """
            request_id = self._generate_request_id()
            start_time = time.time()

            self._logger.info(
                "Processing approve_pr request",
                request_id=request_id,
                pr_url=pr_url[:100],
            )

            # Authenticate request
            client_id = await self._authenticate_request(
                request_id, start_time, api_key
            )

            # Use authenticated client_id for rate limiting
            rate_limit_client_id = client_id or "anonymous"

            try:
                # Check rate limit with client-specific identifier
                self._check_rate_limit(rate_limit_client_id)

                # Validate PR URL
                repo_owner, repo_name, pr_number = (
                    self._input_validator.validate_github_url(pr_url)
                )

                # Get repository instance
                repository = self._github_repository_class(
                    repo_owner, repo_name, pr_number
                )

                # Validate compliment
                if not compliment or not isinstance(compliment, str):
                    raise ValueError("Compliment must be a non-empty string")

                # Approve PR with compliment
                result = await repository.approve_pr_with_comment(
                    pr_url=pr_url,
                    compliment=compliment,
                )

                execution_time = time.time() - start_time
                self._metrics_tracker.track_request("approve_pr", True, execution_time)

                self._logger.info(f"Successfully approved PR\n{result}")
                return result

            except (
                InvalidURLError,
                InvalidRepositoryError,
                InvalidPRNumberError,
                InputSanitizationError,
                SuspiciousOperationError,
            ) as e:
                self._handle_security_exception(e, start_time, request_id, pr_url)

            except ValueError as e:
                self._handle_validation_exception(e, start_time, request_id, pr_url)
            except (
                RuntimeError,
                KeyError,
                AttributeError,
                TypeError,
                ConnectionError,
            ) as e:
                self._handle_runtime_exception(e, start_time, request_id, pr_url)

    def run(self):
        """Start the FastMCP server with configured transport and port.

        Configuration priority (highest to lowest):
        1. Environment variables (MCP_TRANSPORT, MCP_PORT, MCP_HOST, MCP_PATH)
        2. Settings file (settings.toml)
        3. Defaults (http transport, port 9102, host 127.0.0.1, path /mcp)

        Supported transports include "stdio", "http", "sse", and "streamable-http".
        """
        import os

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
