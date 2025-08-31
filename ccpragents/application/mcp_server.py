import re
import time
from typing import Optional, Callable
from fastmcp import FastMCP, Context
from mcp.types import ContentBlock, TextContent
from ccpragents.domain.entities.pr_diff import ExtraPRDiff
from ccpragents.domain.entities.prompt import PRDetails
from ccpragents.domain.usecases import GetPRDiffUseCase
from ccpragents.domain.usecases.prompt import (
    DescribePRUserPromptUseCase,
    ReviewPRUserPromptUseCase,
    UpdateChangelogUserPromptUseCase,
    DescribePRSystemPromptUseCase,
    ReviewPRSystemPromptUseCase,
    UpdateChangelogSystemPromptUseCase,
    ApprovePRUserPromptUseCase,
    ApprovePRSystemPromptUseCase
)
from ccpragents.domain.services.settings import SettingsServiceInterface
from ccpragents.domain.services.cache import CacheServiceInterface
from ccpragents.domain.services.repository_cache import RepositoryCacheServiceInterface
from ccpragents.domain.services.logger import LoggerServiceInterface
from ccpragents.domain.repositories.pr_diff_repository import PRDiffRepositoryInterface


class FastMCPServer:
    '''FastMCP server for fetching GitHub PR diffs with detailed file change information.

    This server provides a tool for retrieving pull request information:
    - get_pr_diff: Fetches PR diff information including file statistics

    Attributes:
        mcp: The FastMCP instance for tool registration and server management
        settings_service: Settings service for configuration
        logger: Logger for logging messages
    '''
    def __init__(self,
                 settings_service: SettingsServiceInterface,
                 cache_service: CacheServiceInterface,
                 repository_cache_service: RepositoryCacheServiceInterface,
                 logger: LoggerServiceInterface,
                 github_repository_class: Callable[[str, str, int], PRDiffRepositoryInterface],
                 describe_pr_user_prompt_use_case: DescribePRUserPromptUseCase,
                 review_pr_user_prompt_use_case: ReviewPRUserPromptUseCase,
                 update_changelog_user_prompt_use_case: UpdateChangelogUserPromptUseCase,
                 describe_pr_system_prompt_use_case: DescribePRSystemPromptUseCase,
                 review_pr_system_prompt_use_case: ReviewPRSystemPromptUseCase,
                 update_changelog_system_prompt_use_case: UpdateChangelogSystemPromptUseCase,
                 approve_pr_user_prompt_use_case: ApprovePRUserPromptUseCase,
                 approve_pr_system_prompt_use_case: ApprovePRSystemPromptUseCase):
        '''Initialize the FastMCP server with dependency injection.

        Args:
            settings_service: Settings service instance implementing SettingsServiceInterface
            cache_service: Cache service instance implementing CacheServiceInterface
            repository_cache_service: Repository cache service instance implementing RepositoryCacheServiceInterface
            logger: Logger instance implementing LoggerServiceInterface
            github_repository_class: GitHub repository class callable that creates PRDiffRepositoryInterface instances
            describe_pr_user_prompt_use_case: Use case for PR description user prompts
            review_pr_user_prompt_use_case: Use case for PR review user prompts
            update_changelog_user_prompt_use_case: Use case for changelog updates user prompts
            describe_pr_system_prompt_use_case: Use case for PR description system prompts
            review_pr_system_prompt_use_case: Use case for PR review system prompts
            update_changelog_system_prompt_use_case: Use case for changelog updates system prompts
            approve_pr_user_prompt_use_case: Use case for PR approval user prompts
            approve_pr_system_prompt_use_case: Use case for PR approval system prompts
        '''
        self._settings_service = settings_service
        self._cache_service = cache_service
        self._repository_cache_service = repository_cache_service
        self._logger = logger
        self._github_repository_class = github_repository_class

        # Initialize prompt use cases
        self._describe_pr_user_prompt_use_case = describe_pr_user_prompt_use_case
        self._review_pr_user_prompt_use_case = review_pr_user_prompt_use_case
        self._update_changelog_user_prompt_use_case = update_changelog_user_prompt_use_case
        self._describe_pr_system_prompt_use_case = describe_pr_system_prompt_use_case
        self._review_pr_system_prompt_use_case = review_pr_system_prompt_use_case
        self._update_changelog_system_prompt_use_case = update_changelog_system_prompt_use_case
        self._approve_pr_user_prompt_use_case = approve_pr_user_prompt_use_case
        self._approve_pr_system_prompt_use_case = approve_pr_system_prompt_use_case

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
            instructions='''
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
''',
            version="0.1.1"
        )

        self._register_tools()
        self._register_prompts()

    def _parse_pr_url(self, pr_url: str) -> tuple[str, str, int]:
        '''Parse GitHub PR URL to extract repository owner, name, and PR number.

        Args:
            pr_url: The GitHub pull request URL to parse

        Returns:
            tuple[str, str, int]: A tuple containing (repo_owner, repo_name, pr_number)

        Raises:
            ValueError: If the URL format is invalid or contains invalid characters
        '''
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
        '''Check if the current request exceeds rate limits.

        Raises:
            RuntimeError: If rate limit is exceeded
        '''
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
        '''Generate a unique request ID for tracking purposes.

        Returns:
            str: Unique request ID in format REQ-{timestamp}-{counter}
        '''
        self._request_counter += 1
        return f"REQ-{int(time.time() * 1000)}-{self._request_counter}"

    def _get_health_status(self) -> dict:
        '''Get health status and metrics for the MCP server.

        Returns:
            dict: Health status and metrics information
        '''
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
        '''Format uptime in human-readable format.'''
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
        '''Calculate success rate percentage.'''
        if self._total_requests == 0:
            return 0.0
        return round((self._successful_requests / self._total_requests) * 100, 2)

    def _register_prompts(self):
        '''Register FastMCP prompts with the server instance.

        This method registers prompts for PR analysis and documentation tasks,
        using the new use case architecture with dependency injection.
        '''
        @self.mcp.prompt()
        async def describe(pr_url: str, commit_messages: str, diff_content: str):
            '''Describe the changes in a pull request.

            Args:
                pr_url: The GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                commit_messages: Commit messages from the PR
                diff_content: Diff content from the PR

            Returns:
                str: Prompt for describing PR changes
            '''
            try:
                repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)
                pr_details = PRDetails(repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)

                return await self._describe_pr_user_prompt_use_case.execute(pr_details, commit_messages, diff_content)
            except Exception as e:
                self._logger.error("Failed to generate describe prompt", pr_url=pr_url, error=str(e))
                raise e

        @self.mcp.prompt()
        async def review(pr_url: str, commit_messages: str, diff_content: str):
            '''Review a pull request for code quality and best practices.

            Args:
                pr_url: The GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                commit_messages: Commit messages from the PR
                diff_content: Diff content from the PR

            Returns:
                str: Prompt for reviewing PR quality
            '''
            try:
                repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)
                pr_details = PRDetails(repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)

                return await self._review_pr_user_prompt_use_case.execute(pr_details, commit_messages, diff_content)
            except Exception as e:
                self._logger.error("Failed to generate review prompt", pr_url=pr_url, error=str(e))
                raise e

        @self.mcp.prompt()
        async def update_changelog(pr_url: str, commit_messages: str, diff_content: str):
            '''Generate changelog entries for a pull request.

            Args:
                pr_url: The GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                commit_messages: Commit messages from the PR
                diff_content: Diff content from the PR

            Returns:
                str: Prompt for generating changelog entries
            '''
            try:
                repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)
                pr_details = PRDetails(repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)
                return await self._update_changelog_user_prompt_use_case.execute(pr_details, commit_messages, diff_content)
            except Exception as e:
                self._logger.error("Failed to generate changelog prompt", pr_url=pr_url, error=str(e))
                raise e

    def _register_tools(self):
        '''Register FastMCP tools with the server instance.

        This method registers the get_pr_diff tool for PR diff information.
        '''
        @self.mcp.tool()
        async def get_pr_diff(pr_url: str, use_cache: bool = True):
            '''Get the diff content for a specific GitHub pull request.

            Args:
                pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                use_cache: Whether to use caching (default: True)
            '''
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
                repository: Optional[PRDiffRepositoryInterface] = self._repository_cache_service.retrieve(repo_owner, repo_name, pr_number)

                if repository is None:
                    # Create new repository instance
                    repository = self._github_repository_class(repo_owner, repo_name, pr_number)
                    self._logger.debug("Created new repository instance",
                                     request_id=request_id, repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)
                else:
                    self._logger.debug("Reusing cached repository instance",
                                     request_id=request_id, repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)

                use_case: GetPRDiffUseCase = GetPRDiffUseCase(repository, cache_service=self._cache_service)
                result: ExtraPRDiff = await use_case.execute(use_cache=use_cache)

                # Cache the repository after it's been used (now it should be initialized)
                if hasattr(repository, '_initialized') and getattr(repository, '_initialized', False):
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



        @self.mcp.tool()
        async def describe_pr(pr_url: str, commit_messages: str, diff_content: str, ctx: Context):
            """Describe the changes in a pull request.

            Args:
                pr_url: The GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                commit_messages: Commit messages from the PR
                diff_content: Diff content from the PR

            Returns:
                str: Description of the PR changes
            """
            try:
                repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)
                pr_details = PRDetails(repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)

                user_prompt = await self._describe_pr_user_prompt_use_case.execute(pr_details, commit_messages, diff_content)
                system_prompt = await self._describe_pr_system_prompt_use_case.execute()

                result: ContentBlock = await ctx.sample(messages=user_prompt, system_prompt=system_prompt)
                self._logger.info(f'Result: {result}')
                return result.text if isinstance(result, TextContent) else str(result)
            except Exception as e:
                self._logger.error("Failed to generate PR description", pr_url=pr_url, error=str(e))
                raise RuntimeError(f"Failed to generate PR description: {e}")

        @self.mcp.tool()
        async def approve_pr(pr_url: str, commit_messages: str, diff_content: str, ctx: Context):
            """Approve a pull request.

            Args:
                pr_url: The GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                commit_messages: Commit messages from the PR
                diff_content: Diff content from the PR

            Returns:
                str: PR approval result
            """
            try:
                repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)
                pr_details = PRDetails(repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)

                return await self._approve_pr_user_prompt_use_case.execute(pr_details, commit_messages, diff_content)
            except Exception as e:
                self._logger.error("Failed to generate PR approval", pr_url=pr_url, error=str(e))
                raise RuntimeError(f"Failed to generate PR approval: {e}")

        @self.mcp.tool()
        async def review_pr(pr_url: str, commit_messages: str, diff_content: str, ctx: Context):
            """Review a pull request for code quality and best practices.

            Args:
                pr_url: The GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                commit_messages: Commit messages from the PR
                diff_content: Diff content from the PR

            Returns:
                str: PR review result
            """
            try:
                repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)
                pr_details = PRDetails(repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)

                return await self._review_pr_user_prompt_use_case.execute(pr_details, commit_messages, diff_content)
            except Exception as e:
                self._logger.error("Failed to generate PR review", pr_url=pr_url, error=str(e))
                raise RuntimeError(f"Failed to generate PR review: {e}")

        @self.mcp.tool()
        async def update_pr_changelog(pr_url: str, commit_messages: str, diff_content: str, ctx: Context):
            """Update changelog entries for a pull request.

            Args:
                pr_url: The GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                commit_messages: Commit messages from the PR
                diff_content: Diff content from the PR

            Returns:
                str: Changelog entries
            """
            try:
                repo_owner, repo_name, pr_number = self._parse_pr_url(pr_url)
                pr_details = PRDetails(repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)

                return await self._update_changelog_user_prompt_use_case.execute(pr_details, commit_messages, diff_content)
            except Exception as e:
                self._logger.error("Failed to generate changelog entries", pr_url=pr_url, error=str(e))
                raise RuntimeError(f"Failed to generate changelog entries: {e}")

    def run(self):
        '''Start the FastMCP server with configured transport and port.

        The server reads configuration from the settings service:
        - mcp.transport: The transport protocol (default: "stdio")
        - mcp.port: The port number for non-stdio transports (default: 9101)
        - mcp.host: The host address for non-stdio transports (default: "127.0.0.1")
        - mcp.path: The path for non-stdio transports (default: "/mcp")

        Supported transports include "stdio", "sse", and other FastMCP transport options.
        '''
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
