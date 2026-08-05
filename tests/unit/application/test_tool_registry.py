"""Comprehensive tests for ToolRegistry."""

import pytest
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from unittest.mock import MagicMock, AsyncMock, patch

from prdiffer.application.tool_registry import ToolRegistry
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.exceptions import (
    InvalidURLError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    GitHubAPIError,
    InputSanitizationError,
)


@dataclass
class ProviderReader:
    result: PRDiff
    commit_sha: str
    diff_calls: list[tuple[str, str, int]] = field(default_factory=list[tuple[str, str, int]])
    commit_calls: list[tuple[str, str, int]] = field(default_factory=list[tuple[str, str, int]])

    async def get_pr_diff(self, repo_owner: str, repo_name: str, pr_number: int) -> PRDiff:
        self.diff_calls.append((repo_owner, repo_name, pr_number))
        return self.result

    async def get_latest_commit_sha(self, repo_owner: str, repo_name: str, pr_number: int) -> str:
        self.commit_calls.append((repo_owner, repo_name, pr_number))
        return self.commit_sha


@dataclass
class RecordingCache:
    lookup_keys: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])
    write_keys: list[tuple[str, str, PRDiff]] = field(default_factory=list[tuple[str, str, PRDiff]])

    def get_cache_key(self, repo_owner: str, repo_name: str, pr_number: int) -> str:
        return f"{repo_owner}/{repo_name}/pr/{pr_number}"

    async def get(self, cache_key: str, commit_sha: str) -> None:
        self.lookup_keys.append((cache_key, commit_sha))
        return None

    async def set(self, cache_key: str, commit_sha: str, diff: PRDiff) -> None:
        self.write_keys.append((cache_key, commit_sha, diff))


@dataclass
class RecordingCoalescer:
    keys: list[str] = field(default_factory=list[str])

    async def coalesce(
        self,
        key: str,
        fetch: Callable[[], Awaitable[PRDiff]],
        timeout: float | None = 30.0,
    ) -> PRDiff:
        self.keys.append(key)
        return await fetch()


class ProviderAwareValidator:
    def sanitize_string(self, value: str, max_length: int = 1000) -> str:
        return value

    def sanitize_for_logging(self, value: str, max_length: int = 200) -> str:
        return value

    def validate_github_url(self, url: str) -> tuple[str, str, int]:
        assert url == "https://github.com/owner/repo/pull/17"
        return "owner", "repo", 17

    def validate_gitlab_url(self, url: str) -> tuple[str, str, int]:
        assert url == "https://gitlab.com/owner/repo/-/merge_requests/17"
        return "owner", "repo", 17


class MCPToolCapture:
    def __init__(self) -> None:
        self.get_pr_diff_tool: Callable[..., Awaitable[PRDiff]] | None = None

    def tool(self) -> Callable[[Callable[..., Awaitable[PRDiff]]], Callable[..., Awaitable[PRDiff]]]:
        def decorator(function: Callable[..., Awaitable[PRDiff]]) -> Callable[..., Awaitable[PRDiff]]:
            if function.__name__ == "get_pr_diff":
                self.get_pr_diff_tool = function
            return function

        return decorator


@pytest.fixture
def mock_pr_diff_service():
    """Create mock PR diff service."""
    return MagicMock()


@pytest.fixture
def mock_cache_service():
    """Create mock cache service."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    return mock


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    mock = MagicMock()
    mock.should_log = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_rate_limiter():
    """Create mock rate limiter."""
    mock = MagicMock()
    mock.check_rate_limit = MagicMock(return_value=True)
    mock.increment_rate_limit = MagicMock()
    mock.get_rate_limit_info = MagicMock(
        return_value={
            "max_requests": 100,
            "window_seconds": 60,
        }
    )
    return mock


@pytest.fixture
def mock_metrics_tracker():
    """Create mock metrics tracker."""
    mock = MagicMock()
    mock.generate_request_id = MagicMock(return_value="test-request-id")
    mock.track_request = MagicMock()
    return mock


@pytest.fixture
def mock_authentication():
    """Create mock authentication."""
    mock = MagicMock()
    mock.authenticate = MagicMock(return_value=(True, "client-123"))
    return mock


@pytest.fixture
def mock_input_validator():
    """Create mock input validator."""
    mock = MagicMock()
    mock.sanitize_string = MagicMock(side_effect=lambda x, **kwargs: x)
    mock.sanitize_for_logging = MagicMock(side_effect=lambda x, **kwargs: x)
    mock.validate_github_url = MagicMock(return_value=("owner", "repo", 123))
    return mock


@pytest.fixture
def mock_request_coalescing():
    """Create mock request coalescing service."""
    mock = MagicMock()
    mock.coalesce = AsyncMock(side_effect=lambda key, fn, timeout=None: fn())
    return mock


@pytest.fixture
def mock_github_repository_class():
    """Create mock GitHub repository class."""
    mock_instance = MagicMock()
    mock_instance.approve_pr_with_comment = AsyncMock(return_value="Approved!")
    return MagicMock(return_value=mock_instance)


@pytest.fixture
def tool_registry(
    mock_pr_diff_service,
    mock_cache_service,
    mock_logger,
    mock_github_repository_class,
    mock_rate_limiter,
    mock_metrics_tracker,
    mock_authentication,
    mock_input_validator,
    mock_request_coalescing,
):
    """Create ToolRegistry with mocked dependencies."""
    return ToolRegistry(
        pr_diff_service=mock_pr_diff_service,
        cache_service=mock_cache_service,
        logger=mock_logger,
        github_repository_class=mock_github_repository_class,
        rate_limiter=mock_rate_limiter,
        metrics_tracker=mock_metrics_tracker,
        authentication=mock_authentication,
        input_validator=mock_input_validator,
        request_coalescing_service=mock_request_coalescing,
    )


@pytest.fixture
def sample_pr_diff():
    """Create sample PRDiff."""
    return PRDiff(
        files=(
            FileDiffResponse(
                path="src/test.py",
                status=EDIT_TYPE.MODIFIED,
                stats=FileStats(additions=10, deletions=5),
                diff="test diff",
            ),
        )
    )


class TestToolRegistryInit:
    """Tests for ToolRegistry initialization."""

    def test_init_with_all_dependencies(
        self,
        mock_pr_diff_service,
        mock_cache_service,
        mock_logger,
        mock_github_repository_class,
        mock_rate_limiter,
        mock_metrics_tracker,
        mock_authentication,
        mock_input_validator,
        mock_request_coalescing,
    ):
        """Test initialization with all dependencies."""
        registry = ToolRegistry(
            pr_diff_service=mock_pr_diff_service,
            cache_service=mock_cache_service,
            logger=mock_logger,
            github_repository_class=mock_github_repository_class,
            rate_limiter=mock_rate_limiter,
            metrics_tracker=mock_metrics_tracker,
            authentication=mock_authentication,
            input_validator=mock_input_validator,
            request_coalescing_service=mock_request_coalescing,
        )

        assert registry._pr_diff_service is mock_pr_diff_service
        assert registry._cache_service is mock_cache_service
        assert registry._logger is mock_logger
        assert registry._authentication is mock_authentication
        assert registry._input_validator is mock_input_validator

    def test_generate_request_id(self, tool_registry, mock_metrics_tracker):
        """Test request ID generation."""
        result = tool_registry._generate_request_id()

        mock_metrics_tracker.generate_request_id.assert_called_once()
        assert result == "test-request-id"


class TestCheckRateLimit:
    """Tests for _check_rate_limit method."""

    def test_check_rate_limit_passes(self, tool_registry, mock_rate_limiter):
        """Test rate limit check passes."""
        tool_registry._check_rate_limit("client-123")

        mock_rate_limiter.check_rate_limit.assert_called_once_with("client-123")
        mock_rate_limiter.increment_rate_limit.assert_called_once_with("client-123")

    def test_check_rate_limit_exceeded(self, tool_registry, mock_rate_limiter):
        """Test rate limit exceeded raises error."""
        mock_rate_limiter.check_rate_limit.return_value = False

        with pytest.raises(RateLimitError):
            tool_registry._check_rate_limit("client-123")


class TestCreateSafeErrorMessage:
    """Tests for _create_safe_error_message method."""

    def test_github_exception(self, tool_registry):
        """Test GithubException message."""
        from github import GithubException

        error = GithubException(500, "Internal error", {})

        result = tool_registry._create_safe_error_message(error)

        assert result == "GitHub API error occurred"

    def test_invalid_url_error(self, tool_registry):
        """Test InvalidURLError message."""
        error = InvalidURLError("Bad URL")

        result = tool_registry._create_safe_error_message(error)

        assert result == "Invalid GitHub PR URL format"

    def test_connection_error(self, tool_registry):
        """Test ConnectionError message."""
        error = ConnectionError("Connection failed")

        result = tool_registry._create_safe_error_message(error)

        assert result == "Connection to GitHub failed"

    def test_timeout_error(self, tool_registry):
        """Test TimeoutError message."""
        error = TimeoutError("Request timed out")

        result = tool_registry._create_safe_error_message(error)

        assert result == "Request timed out"

    def test_value_error(self, tool_registry):
        """Test ValueError message."""
        error = ValueError("Invalid value")

        result = tool_registry._create_safe_error_message(error)

        assert result == "Invalid input value"

    def test_unknown_error(self, tool_registry):
        """Test unknown error message."""
        error = RuntimeError("Unknown error")

        result = tool_registry._create_safe_error_message(error)

        assert result == "Request processing failed"


class TestValidateAndSanitizeParams:
    """Tests for _validate_and_sanitize_params method."""

    def test_validate_valid_url(self, tool_registry, mock_input_validator):
        """Test validating valid URL."""
        mock_input_validator.sanitize_string.return_value = "https://github.com/owner/repo/pull/123"

        with patch("prdiffer.application.tool_registry.parse_pr_url") as mock_parse:
            mock_parse.return_value = ("owner", "repo", 123)
            result = tool_registry._validate_and_sanitize_params("https://github.com/owner/repo/pull/123")

            assert result == ("owner", "repo", 123)

    def test_validate_empty_url(self, tool_registry):
        """Test validating empty URL."""
        with pytest.raises(InputSanitizationError, match="PR URL parameter is required"):
            tool_registry._validate_and_sanitize_params("")


class TestLogMetricsAndReturnSuccess:
    """Tests for _log_metrics_and_return_success method."""

    def test_log_metrics(self, tool_registry, mock_metrics_tracker, mock_logger, sample_pr_diff):
        """Test logging metrics."""
        start_time = 0.0

        result = tool_registry._log_metrics_and_return_success(start_time, sample_pr_diff)

        mock_metrics_tracker.track_request.assert_called_once()
        mock_logger.info.assert_called()
        assert result is sample_pr_diff


class TestHandleSecurityException:
    """Tests for _handle_security_exception method."""

    def test_handle_security_exception(self, tool_registry, mock_metrics_tracker, mock_logger):
        """Test handling security exception."""
        error = InvalidURLError("Invalid URL")

        with pytest.raises(ValidationError):
            tool_registry._handle_security_exception(error, 0.0, "req-123", "https://github.com/owner/repo/pull/123")

        mock_metrics_tracker.track_request.assert_called_once()
        mock_logger.warning.assert_called()


class TestHandleValidationException:
    """Tests for _handle_validation_exception method."""

    def test_handle_validation_exception(self, tool_registry, mock_metrics_tracker, mock_logger):
        """Test handling validation exception."""
        error = ValueError("Invalid value")

        with pytest.raises(ValidationError):
            tool_registry._handle_validation_exception(error, 0.0, "req-123", "https://github.com/owner/repo/pull/123")

        mock_metrics_tracker.track_request.assert_called_once()
        mock_logger.warning.assert_called()


class TestHandleRuntimeException:
    """Tests for _handle_runtime_exception method."""

    def test_handle_runtime_exception(self, tool_registry, mock_metrics_tracker, mock_logger):
        """Test handling runtime exception."""
        error = RuntimeError("Runtime error")

        with pytest.raises(GitHubAPIError):
            tool_registry._handle_runtime_exception(error, 0.0, "req-123", "https://github.com/owner/repo/pull/123")

        mock_metrics_tracker.track_request.assert_called_once()
        mock_logger.error.assert_called()


class TestAuthenticateRequest:
    """Tests for _authenticate_request method."""

    @pytest.mark.anyio
    async def test_authenticate_success(self, tool_registry, mock_authentication):
        """Test successful authentication."""
        result = await tool_registry._authenticate_request("req-123", 0.0, "api-key-123")

        mock_authentication.authenticate.assert_called_once_with("api-key-123")
        assert result == "client-123"

    @pytest.mark.anyio
    async def test_authenticate_no_service(self, tool_registry):
        """Test authentication with no service."""
        tool_registry._authentication = None

        with pytest.raises(AuthenticationError):
            await tool_registry._authenticate_request("req-123", 0.0, "api-key-123")

    @pytest.mark.anyio
    async def test_authenticate_failed(self, tool_registry, mock_authentication):
        """Test failed authentication."""
        mock_authentication.authenticate.return_value = (False, None)

        with pytest.raises(AuthenticationError):
            await tool_registry._authenticate_request("req-123", 0.0, "api-key-123")

    @pytest.mark.anyio
    async def test_authenticate_runtime_error(self, tool_registry, mock_authentication, mock_metrics_tracker):
        """Test authentication with runtime error."""
        mock_authentication.authenticate.side_effect = RuntimeError("Rate limited")

        with pytest.raises(AuthenticationError):
            await tool_registry._authenticate_request("req-123", 0.0, "api-key-123")

        mock_metrics_tracker.track_request.assert_called()


class TestExecuteUseCaseWithCoalescing:
    """Tests for _execute_use_case_with_coalescing method."""

    @pytest.mark.anyio
    async def test_execute_success(self, tool_registry, mock_request_coalescing, sample_pr_diff):
        """Test successful use case execution."""
        mock_request_coalescing.coalesce = AsyncMock(return_value=sample_pr_diff)

        with patch("prdiffer.application.pr_diff_executor.GetPRDiffUseCase") as MockUseCase:
            mock_use_case = MagicMock()
            mock_use_case.execute = AsyncMock(return_value=sample_pr_diff)
            MockUseCase.return_value = mock_use_case

            result = await tool_registry._execute_use_case_with_coalescing("req-123", "owner", "repo", 123)

            assert result is sample_pr_diff

    @pytest.mark.anyio
    async def test_execute_returns_none(self, tool_registry, mock_request_coalescing, mock_logger):
        """Test use case returns None."""
        with patch("prdiffer.application.pr_diff_executor.GetPRDiffUseCase") as MockUseCase:
            mock_use_case = MagicMock()
            mock_use_case.execute = AsyncMock(return_value=None)
            MockUseCase.return_value = mock_use_case

            # The coalesce will call the inner function which raises GitHubAPIError
            async def side_effect(key, fn, timeout=None):
                return await fn()

            mock_request_coalescing.coalesce = AsyncMock(side_effect=side_effect)

            with pytest.raises(GitHubAPIError, match="use case returned None"):
                await tool_registry._execute_use_case_with_coalescing("req-123", "owner", "repo", 123)


class TestRegisterTools:
    """Tests for register_tools method."""

    def test_register_tools(self, tool_registry):
        """Test tool registration."""
        mock_mcp = MagicMock()

        # Mock the decorator
        decorated_tools = []

        def mock_tool_decorator():
            def decorator(func):
                decorated_tools.append(func.__name__)
                return func

            return decorator

        mock_mcp.tool = mock_tool_decorator

        tool_registry.register_tools(mock_mcp)

        assert "get_pr_diff" in decorated_tools
        assert "approve_pr" in decorated_tools


class TestSafeErrorMessages:
    """Tests for all error message mappings."""

    def test_key_error_message(self, tool_registry):
        """Test KeyError message."""
        error = KeyError("missing_key")

        result = tool_registry._create_safe_error_message(error)

        assert result == "Missing required field"

    def test_attribute_error_message(self, tool_registry):
        """Test AttributeError message."""
        error = AttributeError("missing_attribute")

        result = tool_registry._create_safe_error_message(error)

        assert result == "Configuration error"

    def test_type_error_message(self, tool_registry):
        """Test TypeError message."""
        error = TypeError("wrong type")

        result = tool_registry._create_safe_error_message(error)

        assert result == "Invalid input type"


class TestGetPRDiffProviderDispatch:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ("url", "provider", "cache_key", "coalesce_key"),
        [
            ("https://github.com/owner/repo/pull/17", "github", "owner/repo/pr/17", "owner/repo/pr/17"),
            (
                "https://gitlab.com/owner/repo/-/merge_requests/17",
                "gitlab",
                "gitlab:owner/repo/pr/17",
                "https://gitlab.com:gitlab:owner/repo/pr/17",
            ),
        ],
    )
    async def test_registered_get_pr_diff_routes_to_only_the_matching_provider_reader(
        self,
        url: str,
        provider: str,
        cache_key: str,
        coalesce_key: str,
        mock_logger,
        mock_github_repository_class,
        mock_rate_limiter,
        mock_metrics_tracker,
        mock_authentication,
    ) -> None:
        # Given
        github_diff = PRDiff(files=(FileDiffResponse("github.py", EDIT_TYPE.MODIFIED, FileStats(additions=1, deletions=0), "+github"),))
        gitlab_diff = PRDiff(files=(FileDiffResponse("gitlab.py", EDIT_TYPE.ADDED, FileStats(additions=1, deletions=0), "+gitlab"),))
        github_reader = ProviderReader(github_diff, "github-commit")
        gitlab_reader = ProviderReader(gitlab_diff, "gitlab-commit")
        cache = RecordingCache()
        coalescer = RecordingCoalescer()
        registry_arguments: dict[str, object] = {
            "pr_diff_service": github_reader,
            "cache_service": cache,
            "logger": mock_logger,
            "github_repository_class": mock_github_repository_class,
            "gitlab_reader": gitlab_reader,
            "rate_limiter": mock_rate_limiter,
            "metrics_tracker": mock_metrics_tracker,
            "authentication": mock_authentication,
            "input_validator": ProviderAwareValidator(),
            "request_coalescing_service": coalescer,
        }
        registry = ToolRegistry.__new__(ToolRegistry)
        initialize_registry: Callable[..., None] = getattr(registry, "__init__")
        initialize_registry(**registry_arguments)
        mcp = MCPToolCapture()
        register_tools: Callable[[MCPToolCapture], None] = getattr(registry, "register_tools")
        register_tools(mcp)
        get_pr_diff = mcp.get_pr_diff_tool
        assert get_pr_diff is not None
        readers = {"github": github_reader, "gitlab": gitlab_reader}
        expected_diff = {"github": github_diff, "gitlab": gitlab_diff}[provider]
        selected_reader = readers[provider]
        other_reader = readers[{"github": "gitlab", "gitlab": "github"}[provider]]

        # When
        result = await get_pr_diff(url, None)

        # Then
        assert result is expected_diff
        assert selected_reader.commit_calls == [("owner", "repo", 17)]
        assert selected_reader.diff_calls == [("owner", "repo", 17)]
        assert other_reader.commit_calls == []
        assert other_reader.diff_calls == []
        assert cache.lookup_keys == [(cache_key, f"{provider}-commit")]
        assert cache.write_keys == [(cache_key, f"{provider}-commit", expected_diff)]
        assert coalescer.keys == [coalesce_key]


@pytest.mark.unit
@pytest.mark.asyncio
class TestFullDiffIncompleteToolError:
    async def test_full_diff_incomplete_raises_structured_tool_error(
        self,
        mock_logger,
        mock_github_repository_class,
        mock_rate_limiter,
        mock_metrics_tracker,
        mock_authentication,
    ) -> None:
        import json
        from fastmcp.exceptions import ToolError
        from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason

        class BoomReader:
            async def get_pr_diff(self, repo_owner: str, repo_name: str, pr_number: int):
                raise FullDiffIncompleteError(
                    FullDiffIncompleteReason.BINARY_CONTENT,
                    path="bin.dat",
                    previous_path="old.bin",
                    observed=10,
                    limit=5,
                )

            async def get_latest_commit_sha(self, repo_owner: str, repo_name: str, pr_number: int) -> str:
                return "sha"

        class PassthroughCoalescer:
            async def coalesce(self, key, fn, timeout=None):
                return await fn()

            def clear(self) -> None:
                return None

            def get_stats(self) -> dict:
                return {}

        registry = ToolRegistry(
            pr_diff_service=BoomReader(),
            cache_service=RecordingCache(),
            logger=mock_logger,
            github_repository_class=mock_github_repository_class,
            rate_limiter=mock_rate_limiter,
            metrics_tracker=mock_metrics_tracker,
            authentication=mock_authentication,
            input_validator=ProviderAwareValidator(),
            request_coalescing_service=PassthroughCoalescer(),
        )
        mcp = MCPToolCapture()
        registry.register_tools(mcp)
        get_pr_diff = mcp.get_pr_diff_tool
        assert get_pr_diff is not None

        with pytest.raises(ToolError) as exc_info:
            await get_pr_diff("https://github.com/owner/repo/pull/17", None)

        payload = json.loads(str(exc_info.value))
        assert list(payload.keys()) == ["error_code", "message", "details"]
        assert payload["error_code"] == "E5020_FULL_DIFF_INCOMPLETE"
        assert payload["details"]["reason"] == "BINARY_CONTENT"
        assert payload["details"]["path"] == "bin.dat"
        assert payload["details"]["previous_path"] == "old.bin"
        assert payload["details"]["observed"] == 10
        assert payload["details"]["limit"] == 5
        assert "files" not in payload
        assert "token" not in json.dumps(payload)
        mock_metrics_tracker.track_request.assert_called()
        # Exactly one failure metric for this tool invocation
        fail_calls = [c for c in mock_metrics_tracker.track_request.call_args_list if c.args[:2] == ("get_pr_diff", False)]
        assert len(fail_calls) == 1

    async def test_non_e5020_errors_not_remapped_to_tool_error_json(
        self,
        mock_logger,
        mock_github_repository_class,
        mock_rate_limiter,
        mock_metrics_tracker,
        mock_authentication,
    ) -> None:
        from prdiffer.domain.exceptions import AuthenticationError
        from prdiffer.domain.error_codes import E2006_GITLAB_AUTH_FAILED

        class AuthBoom:
            async def get_pr_diff(self, *args):
                raise AuthenticationError("nope", error_code=E2006_GITLAB_AUTH_FAILED)

            async def get_latest_commit_sha(self, *args) -> str:
                return "sha"

        class PassthroughCoalescer:
            async def coalesce(self, key, fn, timeout=None):
                return await fn()

            def clear(self) -> None:
                return None

            def get_stats(self) -> dict:
                return {}

        registry = ToolRegistry(
            pr_diff_service=AuthBoom(),
            cache_service=RecordingCache(),
            logger=mock_logger,
            github_repository_class=mock_github_repository_class,
            rate_limiter=mock_rate_limiter,
            metrics_tracker=mock_metrics_tracker,
            authentication=mock_authentication,
            input_validator=ProviderAwareValidator(),
            request_coalescing_service=PassthroughCoalescer(),
        )
        mcp = MCPToolCapture()
        registry.register_tools(mcp)
        get_pr_diff = mcp.get_pr_diff_tool
        assert get_pr_diff is not None

        with pytest.raises(AuthenticationError) as exc_info:
            await get_pr_diff("https://github.com/owner/repo/pull/17", None)
        assert exc_info.value.error_code is E2006_GITLAB_AUTH_FAILED
