import re
import time
from fastmcp import FastMCP
from ccpragents.domain.entities.pr_diff import ExtraPRDiff
from ccpragents.domain.usecases import GetPRDiffUseCase
from ccpragents.infrastructure.github_repository import GitHubPRDiffRepository
from ccpragents.infrastructure.settings import get_settings_service
from ccpragents.infrastructure.cache_service import get_cache_service
from ccpragents.infrastructure.repository_cache_service import get_repository_cache_service
from ccpragents.infrastructure.logging.console_logger import get_logger


class FastMCPServer:
    """FastMCP server for fetching GitHub PR diffs with detailed file change information.

    This server provides a tool for retrieving pull request information:
    - get_pr_diff: Fetches PR diff information including file statistics

    Attributes:
        mcp: The FastMCP instance for tool registration and server management
        settings_service: Settings service for configuration
        logger: Logger for logging messages
    """
    def __init__(self,
                 settings_service=None,
                 cache_service=None,
                 repository_cache_service=None,
                 logger=None,
                 github_repository_class=None):
        """Initialize the FastMCP server with optional dependency injection.

        Args:
            settings_service: Settings service instance (default: get_settings_service())
            cache_service: Cache service instance (default: get_cache_service())
            repository_cache_service: Repository cache service instance (default: get_repository_cache_service())
            logger: Logger instance (default: get_logger())
            github_repository_class: GitHub repository class for testing (default: GitHubPRDiffRepository)
        """
        self._settings_service = settings_service or get_settings_service()
        self._cache_service = cache_service or get_cache_service()
        self._repository_cache_service = repository_cache_service or get_repository_cache_service()
        self._logger = logger or get_logger()
        self._github_repository_class = github_repository_class or GitHubPRDiffRepository

        # Rate limiting configuration
        self._rate_limit_requests = 100  # Max requests per minute
        self._rate_limit_window = 60  # 60 second window
        self._request_timestamps = []  # Track request timestamps for rate limiting

        # Request tracking for structured logging
        self._request_counter = 0

        # Metrics tracking
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._start_time = time.time()

        self._logger.info("Initializing FastMCP server", component="mcp_server")

        self.mcp = FastMCP(
            name="ccpragents",
            instructions="""
GitHub PR Diff Fetcher MCP - A powerful tool for retrieving detailed pull request information from GitHub.

This MCP provides a tool for fetching PR diff information:

get_pr_diff - Fetches PR diff information including:
- PR number, repository owner, and repository name
- Diff content for the complete changeset
- Base and head commit SHAs
- Statistics: changed files count, additions, deletions
- File change details with patch content and line numbers
- Commit messages
- Reviewers
- Labels
- Milestone

Usage example:
- Fetch PR diff: get_pr_diff("https://github.com/owner/repo/pull/123")

The tool returns structured data with complete file change information, making it ideal for:
- Code review automation
- PR analysis and reporting
- Integration with CI/CD pipelines
- Change tracking and audit logging
- Code analysis and refactoring
- Code understanding and documentation
""",
            version="0.1.1"
        )

        self._register_tools()
        self._register_prompts()

    def _parse_pr_url(self, pr_url: str) -> tuple[str, str, int]:
        """Parse GitHub PR URL to extract repository owner, name, and PR number.

        Args:
            pr_url: The GitHub pull request URL to parse

        Returns:
            tuple[str, str, int]: A tuple containing (repo_owner, repo_name, pr_number)

        Raises:
            ValueError: If the URL format is invalid or contains invalid characters
        """
        if not pr_url:
            raise ValueError("PR URL cannot be empty")

        # Trim whitespace and validate basic URL structure
        pr_url = pr_url.strip()
        if not pr_url.startswith('https://github.com/'):
            raise ValueError("PR URL must be a GitHub URL starting with https://github.com/")

        # Pattern to match GitHub PR URLs with validation
        pattern = r"^https://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/pull/(\d+)/?$"
        match = re.match(pattern, pr_url)

        if not match:
            # Provide more helpful error message
            raise ValueError(
                f"Invalid GitHub PR URL format: {pr_url}. "
                "Expected format: https://github.com/owner/repo/pull/123"
            )

        repo_owner = match.group(1)
        repo_name = match.group(2)
        pr_number = int(match.group(3))

        # Additional validation
        if not repo_owner:
            raise ValueError("Repository owner cannot be empty")
        if not repo_name:
            raise ValueError("Repository name cannot be empty")
        if pr_number <= 0:
            raise ValueError(f"PR number must be positive, got {pr_number}")

        return repo_owner, repo_name, pr_number

    def _check_rate_limit(self):
        """Check if the current request exceeds rate limits.

        Raises:
            RuntimeError: If rate limit is exceeded
        """
        import time

        current_time = time.time()

        # Remove timestamps outside the rate limit window
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if current_time - ts < self._rate_limit_window
        ]

        # Check if we've exceeded the rate limit
        if len(self._request_timestamps) >= self._rate_limit_requests:
            raise RuntimeError(
                f"Rate limit exceeded. Maximum {self._rate_limit_requests} "
                f"requests per {self._rate_limit_window} seconds."
            )

        # Add current timestamp
        self._request_timestamps.append(current_time)


    def _generate_request_id(self) -> str:
        """Generate a unique request ID for tracking purposes.

        Returns:
            str: Unique request ID in format REQ-{timestamp}-{counter}
        """
        self._request_counter += 1
        return f"REQ-{int(time.time() * 1000)}-{self._request_counter}"

    def _get_health_status(self) -> dict:
        """Get health status and metrics for the MCP server.

        Returns:
            dict: Health status and metrics information
        """
        current_time = time.time()
        uptime_seconds = current_time - self._start_time

        return {
            "status": "healthy",
            "uptime_seconds": uptime_seconds,
            "uptime_human": self._format_uptime(uptime_seconds),
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "success_rate": self._calculate_success_rate(),
            "current_rate": len(self._request_timestamps),
            "rate_limit": self._rate_limit_requests,
            "rate_limit_window": self._rate_limit_window
        }

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if days > 0:
            return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(secs)}s"
        elif hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(secs)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(secs)}s"
        else:
            return f"{int(secs)}s"

    def _calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self._total_requests == 0:
            return 0.0
        return round((self._successful_requests / self._total_requests) * 100, 2)

    def _register_prompts(self):
        """Register FastMCP prompts with the server instance.

        This method registers prompts for PR analysis and documentation tasks.
        """
        @self.mcp.prompt()
        def describe(pr_url: str, pr_commit_messages: str, pr_diff: str):
            """Describe the changes in a pull request."""
            return "Describe the changes in this pull request, highlighting key modifications and their impact."

        @self.mcp.prompt()
        def review(pr_url: str, pr_commit_messages: str, pr_diff: str):
            """Review a pull request for code quality and best practices."""
            return "Review this pull request for code quality, best practices, and potential issues."

        @self.mcp.prompt()
        def update_changelog(pr_url: str, pr_commit_messages: str, pr_diff: str):
            """Generate changelog entries for a pull request."""
            return "Generate appropriate changelog entries for the changes in this pull request."

    def _register_tools(self):
        """Register FastMCP tools with the server instance.

        This method registers the get_pr_diff tool for PR diff information.
        """
        @self.mcp.tool()
        async def get_pr_diff(pr_url: str, use_cache: bool = True):
            """Get the diff content for a specific GitHub pull request.

            Args:
                pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                use_cache: Whether to use caching (default: True)
            """
            # Generate request ID for tracing
            request_id = self._generate_request_id()

            self._logger.info("Processing get_pr_diff request",
                           request_id=request_id, pr_url=pr_url, use_cache=use_cache)

            try:
                # Track total requests
                self._total_requests += 1

                # Check rate limit
                self._check_rate_limit()

                # Validate input parameters
                if not pr_url:
                    raise ValueError("PR URL parameter is required")

                if not isinstance(use_cache, bool):
                    raise ValueError("use_cache parameter must be a boolean")

                repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)

                # Try to get repository from cache first
                repository = self._repository_cache_service.retrieve(repo_owner, repo_name, pr_number)

                if repository is None:
                    # Create new repository instance
                    repository: GitHubPRDiffRepository = self._github_repository_class(repo_owner, repo_name, pr_number)
                    self._logger.debug("Created new repository instance",
                                     request_id=request_id, repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)
                else:
                    self._logger.debug("Reusing cached repository instance",
                                     request_id=request_id, repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)

                use_case: GetPRDiffUseCase = GetPRDiffUseCase(repository, cache_service=self._cache_service)
                result: ExtraPRDiff = await use_case.execute(use_cache=use_cache)

                # Cache the repository after it's been used (now it should be initialized)
                if repository._initialized:
                    cache_success = self._repository_cache_service.insert(repository)
                    if cache_success:
                        self._logger.debug("Cached repository instance after initialization",
                                         request_id=request_id, repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)

                response = result.model_dump_json()

                # Track successful request
                self._successful_requests += 1

                self._logger.info("Successfully fetched PR diff",
                               request_id=request_id, repo_owner=repo_owner, repo_name=repo_name,
                               pr_number=pr_number, cached=use_cache, changed_files=result.changed_files)
                return response

            except ValueError as e:
                # Track failed request
                self._failed_requests += 1

                # Validation errors - provide clear error messages
                self._logger.warning("Validation error in PR diff request",
                                  request_id=request_id, pr_url=pr_url, error=str(e), use_cache=use_cache)
                raise ValueError(f"Invalid request: {e}")

            except Exception as e:
                # Track failed request
                self._failed_requests += 1

                # GitHub API or other unexpected errors
                self._logger.error("Failed to fetch PR diff",
                                request_id=request_id, pr_url=pr_url, error=str(e), use_cache=use_cache)
                # Re-raise with consistent error format
                raise RuntimeError(f"Failed to fetch PR diff: {e}")



    def run(self):
        """Start the FastMCP server with configured transport and port.

        The server reads configuration from the settings service:
        - mcp.transport: The transport protocol (default: "stdio")
        - mcp.port: The port number for non-stdio transports (default: 9101)
        - mcp.host: The host address for non-stdio transports (default: "127.0.0.1")
        - mcp.path: The path for non-stdio transports (default: "/mcp")

        Supported transports include "stdio", "sse", and other FastMCP transport options.
        """
        # Get MCP settings from configuration
        transport = self._settings_service.get("mcp.transport", "stdio")
        port = self._settings_service.get("mcp.port", 9101)
        host = self._settings_service.get("mcp.host", "127.0.0.1")
        path = self._settings_service.get("mcp.path", "/mcp")

        if transport == "stdio":
            self._logger.info("Running MCP server with stdio transport")
            self.mcp.run(transport="stdio")
        else:
            self._logger.info(f"Running MCP server with {transport} transport on {host}:{port}{path}")
            self.mcp.run(transport=transport, port=port, host=host, path=path)
