"""Tool registration module for FastMCP server.

This module extracts tool registration logic from mcp_server.py,
providing cleaner separation of concerns.
"""

import time
import hashlib
import json
from dataclasses import asdict
from typing import Callable, NoReturn

from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.usecases.pr_diff_usecases import GetPRDiffUseCase
from prdiffer.domain.services.pr_diff_service import PRDiffServiceInterface
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.logger import LoggerServiceInterface, LogLevel
from prdiffer.domain.interfaces.protocols import (
    RateLimiterProtocol,
    MetricsTrackerProtocol,
    AuthenticationProtocol,
)
from prdiffer.infrastructure.security.input_validator import InputValidator
from prdiffer.infrastructure.utils.coalescing import RequestCoalescingService
from prdiffer.application.utils.pr_url_parser import parse_pr_url

from prdiffer.domain.exceptions import (
    InvalidURLError,
    InvalidRepositoryError,
    InvalidPRNumberError,
    InputSanitizationError,
    SuspiciousOperationError,
    ValidationError,
    AuthenticationError,
    GitHubAPIError,
    RateLimitError,
)
from prdiffer.domain.errors import (
    E1001_INVALID_URL,
    E2002_AUTH_FAILED,
    E3001_RATE_LIMITED,
    E5002_GITHUB_API_ERROR,
)


class ToolRegistry:
    """Registry for FastMCP tools.

    This class handles registration of MCP tools including get_pr_diff and approve_pr.

    Attributes:
        pr_diff_service: PR diff service for retrieving PR information
        cache_service: Cache service for performance optimization
        logger: Logger for tracking operations
        github_repository_class: Factory for creating repository instances
        rate_limiter: Rate limiter for API protection
        metrics_tracker: Metrics tracking for monitoring
        authentication: Authentication service for API access control
        input_validator: Input validation service
        request_coalescing: Request coalescing for concurrent request optimization
    """

    def __init__(
        self,
        pr_diff_service: PRDiffServiceInterface,
        cache_service: CacheServiceInterface,
        logger: LoggerServiceInterface,
        github_repository_class: Callable,
        rate_limiter: RateLimiterProtocol,
        metrics_tracker: MetricsTrackerProtocol,
        authentication: AuthenticationProtocol | None = None,
        input_validator: InputValidator | None = None,
        request_coalescing_service: RequestCoalescingService | None = None,
    ):
        """Initialize ToolRegistry with dependencies.

        Args:
            pr_diff_service: PR diff service instance
            cache_service: Cache service instance
            logger: Logger instance
            github_repository_class: Repository factory callable
            rate_limiter: Rate limiter protocol
            metrics_tracker: Metrics tracker protocol
            authentication: Optional authentication protocol
            input_validator: Optional input validator
            request_coalescing_service: Optional request coalescing service
        """
        self._pr_diff_service = pr_diff_service
        self._cache_service = cache_service
        self._logger = logger
        self._github_repository_class = github_repository_class
        self._rate_limiter = rate_limiter
        self._metrics_tracker = metrics_tracker
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
            from prdiffer.infrastructure.utils.coalescing import (
                get_request_coalescing_service,
            )

            self._request_coalescing = get_request_coalescing_service()
        else:
            self._request_coalescing = request_coalescing_service

    def _generate_request_id(self) -> str:
        """Generate a unique request ID for tracking purposes.

        Returns:
            str: Unique request ID
        """
        return self._metrics_tracker.generate_request_id()

    def _check_rate_limit(self, client_id: str = 'global'):
        """Check if the current request exceeds rate limits.

        Args:
            client_id: Unique identifier for rate limiting

        Raises:
            RuntimeError: If rate limit is exceeded
        """
        if not self._rate_limiter.check_rate_limit(client_id):
            rate_info = self._rate_limiter.get_rate_limit_info()
            raise RateLimitError(
                f"Rate limit exceeded for client '{client_id}'. Maximum {rate_info['max_requests']} requests per {rate_info['window_seconds']} seconds.",
                error_code=E3001_RATE_LIMITED,
            )
        self._rate_limiter.increment_rate_limit(client_id)

    async def _authenticate_request(self, request_id: str, start_time: float, api_key: str | None) -> str | None:
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
            if self._authentication is None:
                raise AuthenticationError(
                    'Authentication service not configured',
                    error_code=E2002_AUTH_FAILED,
                )
            is_authenticated, client_id = self._authentication.authenticate(api_key)
        except RuntimeError as e:
            execution_time = time.time() - start_time
            self._metrics_tracker.track_request('get_pr_diff', False, execution_time)
            self._logger.warning(
                'Authentication rate limited',
                request_id=request_id,
                error=str(e),
            )
            raise AuthenticationError(str(e), error_code=E2002_AUTH_FAILED)

        if not is_authenticated:
            self._logger.warning('Authentication failed', request_id=request_id)
            raise AuthenticationError(
                "Authentication failed. Please provide a valid API key via 'api_key' parameter.",
                error_code=E2002_AUTH_FAILED,
            )

        return client_id

    def _create_safe_error_message(self, exception: Exception) -> str:
        """Create a safe error message that doesn't expose internal details.

        Args:
            exception: The exception to create a safe message for

        Returns:
            str: A safe error message suitable for external consumption
        """
        safe_messages = {
            'GithubException': 'GitHub API error occurred',
            'RateLimitExceededException': 'API rate limit exceeded. Please try again later',
            'UnknownObjectException': 'Repository or PR not found',
            'BadCredentialsException': 'GitHub authentication failed',
            'TwoFactorException': 'Two-factor authentication required',
            'InvalidURLError': 'Invalid GitHub PR URL format',
            'InvalidRepositoryError': 'Invalid repository identifier',
            'InvalidPRNumberError': 'Invalid pull request number',
            'InputSanitizationError': 'Invalid input parameters',
            'SuspiciousOperationError': 'Request contains suspicious patterns',
            'ConnectionError': 'Connection to GitHub failed',
            'TimeoutError': 'Request timed out',
            'SSLError': 'Secure connection failed',
            'ValueError': 'Invalid input value',
            'TypeError': 'Invalid input type',
            'KeyError': 'Missing required field',
            'AttributeError': 'Configuration error',
        }

        exception_type = type(exception).__name__

        if exception_type in safe_messages:
            return safe_messages[exception_type]

        return 'Request processing failed'

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
            raise InputSanitizationError('PR URL parameter is required')

        pr_url = self._input_validator.sanitize_string(pr_url, max_length=2000)

        return parse_pr_url(pr_url, self._input_validator)

    async def _execute_use_case_with_coalescing(self, request_id: str, repo_owner: str, repo_name: str, pr_number: int) -> PRDiff:
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
        coalesce_key = f'{repo_owner}/{repo_name}/pr/{pr_number}'

        async def fetch_pr_diff() -> PRDiff:
            """Fetch PR diff - will be coalesced if multiple requests arrive."""
            use_case = GetPRDiffUseCase(
                pr_diff_service=self._pr_diff_service,
                cache_service=self._cache_service,
            )
            result = await use_case.execute(repo_owner=repo_owner, repo_name=repo_name, pr_number=pr_number)

            if result is None:
                self._logger.error(
                    'Use case returned None for PR diff',
                    request_id=request_id,
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    pr_number=pr_number,
                )
                raise GitHubAPIError(
                    'Failed to get PR diff - use case returned None',
                    error_code=E5002_GITHUB_API_ERROR,
                )

            return result

        return await self._request_coalescing.coalesce(coalesce_key, fetch_pr_diff)

    def _log_metrics_and_return_success(self, start_time: float, pr_diff: PRDiff) -> PRDiff:
        """Log successful request metrics and return PR diff result.

        Args:
            start_time: Request start time
            pr_diff: The PR diff result to return

        Returns:
            PRDiff: The unchanged PR diff result
        """
        execution_time = time.time() - start_time
        self._metrics_tracker.track_request('get_pr_diff', True, execution_time)

        diff_size = len(pr_diff.files)
        diff_hash = hashlib.md5(str(pr_diff.files).encode()).hexdigest()[:8]

        self._logger.info(f'Successfully fetched PR diff - files: {diff_size}, hash: {diff_hash}...')

        if self._logger.should_log(LogLevel.DEBUG):
            sanitized_preview = self._input_validator.sanitize_for_logging(
                f'Files: {len(pr_diff.files)}, preview: {pr_diff.files[:2] if pr_diff.files else []}',
                max_length=500,
            )
            self._logger.debug(f'PR diff content preview (sanitized): {sanitized_preview}')
            sanitized_json = self._input_validator.sanitize_for_logging(
                json.dumps(asdict(pr_diff), indent=2),
                max_length=2000,
            )
            self._logger.debug(f'PR Diff (Pretty JSON, sanitized):\n{sanitized_json}')

        return pr_diff

    def _handle_security_exception(self, exception: Exception, start_time: float, request_id: str, pr_url: str) -> NoReturn:
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
        self._metrics_tracker.track_request('get_pr_diff', False, execution_time)

        self._logger.warning(
            'Security validation error in PR diff request',
            request_id=request_id,
            pr_url=self._input_validator.sanitize_for_logging(pr_url) if pr_url else None,
            error=str(exception),
            error_type=type(exception).__name__,
        )

        safe_message = self._create_safe_error_message(exception)
        raise ValidationError(f'Invalid request: {safe_message}', error_code=E1001_INVALID_URL)

    def _handle_validation_exception(self, exception: Exception, start_time: float, request_id: str, pr_url: str) -> NoReturn:
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
        self._metrics_tracker.track_request('get_pr_diff', False, execution_time)

        self._logger.warning(
            'Validation error in PR diff request',
            request_id=request_id,
            pr_url=self._input_validator.sanitize_for_logging(pr_url) if pr_url else None,
            error=str(exception),
        )

        safe_message = self._create_safe_error_message(exception)
        raise ValidationError(f'Invalid request: {safe_message}', error_code=E1001_INVALID_URL)

    def _handle_runtime_exception(self, exception: Exception, start_time: float, request_id: str, pr_url: str) -> NoReturn:
        """Handle runtime exceptions with logging and re-raising.

        Args:
            exception: The runtime exception to handle
            start_time: Request start time for metrics
            request_id: Unique request identifier
            pr_url: The PR URL (sanitized for logging)

        Raises:
            RuntimeError: Always raises with safe error message
        """
        execution_time = time.time() - start_time
        self._metrics_tracker.track_request('get_pr_diff', False, execution_time)

        self._logger.error(
            'Failed to fetch PR diff',
            request_id=request_id,
            pr_url=self._input_validator.sanitize_for_logging(pr_url) if pr_url else None,
            error=str(exception),
            error_type=type(exception).__name__,
        )

        safe_message = self._create_safe_error_message(exception)
        raise GitHubAPIError(
            f'Failed to fetch PR diff: {safe_message}',
            error_code=E5002_GITHUB_API_ERROR,
        )

    def register_tools(self, mcp):
        """Register FastMCP tools with the server instance.

        This method registers the get_pr_diff, approve_pr, and describe_pr tools.

        Args:
            mcp: The FastMCP server instance
        """

        @mcp.tool()
        async def get_pr_diff(pr_url: str, api_key: str | None = None) -> PRDiff:
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
                'Processing get_pr_diff request',
                request_id=request_id,
                pr_url=pr_url,
            )

            # Authenticate request
            client_id = await self._authenticate_request(request_id, start_time, api_key)

            rate_limit_client_id = client_id or 'anonymous'

            try:
                self._check_rate_limit(rate_limit_client_id)

                repo_owner, repo_name, pr_number = self._validate_and_sanitize_params(pr_url)

                pr_diff = await self._execute_use_case_with_coalescing(request_id, repo_owner, repo_name, pr_number)

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

        @mcp.tool()
        async def approve_pr(pr_url: str, compliment: str, api_key: str | None = None) -> str:
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
                'Processing approve_pr request',
                request_id=request_id,
                pr_url=pr_url[:100],
            )

            client_id = await self._authenticate_request(request_id, start_time, api_key)

            rate_limit_client_id = client_id or 'anonymous'

            try:
                self._check_rate_limit(rate_limit_client_id)

                repo_owner, repo_name, pr_number = self._input_validator.validate_github_url(pr_url)

                repository = self._github_repository_class(repo_owner, repo_name, pr_number)

                if not compliment or not isinstance(compliment, str):
                    raise ValidationError(
                        'Compliment must be a non-empty string',
                        error_code=E1001_INVALID_URL,
                    )

                result = await repository.approve_pr_with_comment(
                    pr_url=pr_url,
                    compliment=compliment,
                )

                execution_time = time.time() - start_time
                self._metrics_tracker.track_request('approve_pr', True, execution_time)

                self._logger.info(f'Successfully approved PR\n{result}')
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

        @mcp.tool()
        async def describe_pr(pr_url: str, pr_description: str, api_key: str | None = None) -> str:
            """Update a GitHub PR description/body.

            This method updates the description of a pull request with the provided text.

            Args:
                pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
                pr_description: The new description text to set on the PR
                api_key: Optional API key for authentication (required if authentication is enabled)

            Returns:
                str: Success message indicating PR description was updated

            Raises:
                ValueError: If authentication fails, URL is invalid, or description is missing
                RuntimeError: If rate limit is exceeded or API request fails
            """
            request_id = self._generate_request_id()
            start_time = time.time()

            self._logger.info(
                'Processing describe_pr request',
                request_id=request_id,
                pr_url=pr_url[:100],
            )

            client_id = await self._authenticate_request(request_id, start_time, api_key)

            rate_limit_client_id = client_id or 'anonymous'

            try:
                self._check_rate_limit(rate_limit_client_id)

                repo_owner, repo_name, pr_number = self._input_validator.validate_github_url(pr_url)

                repository = self._github_repository_class(repo_owner, repo_name, pr_number)

                if not pr_description or not isinstance(pr_description, str):
                    raise ValidationError(
                        'PR description must be a non-empty string',
                        error_code=E1001_INVALID_URL,
                    )

                result = await repository.update_pr_description(
                    pr_url=pr_url,
                    description=pr_description,
                )

                execution_time = time.time() - start_time
                self._metrics_tracker.track_request('describe_pr', True, execution_time)

                self._logger.info(f'Successfully updated PR description\n{result}')
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
