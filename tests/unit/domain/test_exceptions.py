"""Tests for domain exception hierarchy and helper functions."""

import pytest

from prdiffer.domain.errors import ErrorCode, ErrorCategory
from prdiffer.domain.exceptions import (
    PRDifferException,
    AuthenticationError,
    InvalidTokenError,
    ExpiredTokenError,
    MissingTokenError,
    AuthorizationError,
    InsufficientPermissionsError,
    RateLimitError,
    GlobalRateLimitError,
    UserRateLimitError,
    ValidationError,
    InvalidURLError,
    InvalidRepositoryError,
    InvalidPRNumberError,
    UnsupportedFormatError,
    GitHubAPIError,
    GitLabAPIError,
    RepositoryNotFoundError,
    PRNotFoundError,
    FileNotFoundError,
    GitHubAuthenticationError,
    GitHubConnectionError,
    GitHubRateLimitError,
    CacheError,
    CacheInvalidationError,
    CacheCorruptionError,
    ConfigurationError,
    MissingConfigurationError,
    InvalidConfigurationError,
    SecretsError,
    ProcessingError,
    DiffGenerationError,
    FileProcessingError,
    PatternMatchingError,
    ResourceError,
    ResourceExhaustedError,
    MemoryLimitError,
    TimeoutError,
    SecurityError,
    SuspiciousOperationError,
    InputSanitizationError,
    SignatureVerificationError,
    get_exception_details,
    wrap_github_exception,
)


# ---------------------------------------------------------------------------
# PRDifferException base
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPRDifferException:
    """Test base exception."""

    def test_message_stored(self):
        exc = PRDifferException("something broke")
        assert exc.message == "something broke"

    def test_default_error_code(self):
        exc = PRDifferException("err")
        assert exc.error_code.code == "E5001"

    def test_custom_error_code(self):
        code = ErrorCode(
            code="E1001",
            name="TEST",
            message="test",
            remediation="fix",
            category=ErrorCategory.INPUT_VALIDATION,
        )
        exc = PRDifferException("err", error_code=code)
        assert exc.error_code.code == "E1001"

    def test_details_default_empty(self):
        exc = PRDifferException("err")
        assert exc.details == {}

    def test_details_stored(self):
        exc = PRDifferException("err", details={"key": "val"})
        assert exc.details == {"key": "val"}

    def test_str_includes_error_code(self):
        exc = PRDifferException("some error")
        s = str(exc)
        assert "E5001" in s
        assert "some error" in s

    def test_is_exception(self):
        exc = PRDifferException("err")
        assert isinstance(exc, Exception)


# ---------------------------------------------------------------------------
# Inheritance hierarchy
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExceptionHierarchy:
    """Test that all exceptions have correct inheritance."""

    def test_auth_hierarchy(self):
        assert issubclass(AuthenticationError, PRDifferException)
        assert issubclass(InvalidTokenError, AuthenticationError)
        assert issubclass(ExpiredTokenError, AuthenticationError)
        assert issubclass(MissingTokenError, AuthenticationError)

    def test_authorization_hierarchy(self):
        assert issubclass(AuthorizationError, PRDifferException)
        assert issubclass(InsufficientPermissionsError, AuthorizationError)

    def test_rate_limit_hierarchy(self):
        assert issubclass(RateLimitError, PRDifferException)
        assert issubclass(GlobalRateLimitError, RateLimitError)
        assert issubclass(UserRateLimitError, RateLimitError)

    def test_validation_hierarchy(self):
        assert issubclass(ValidationError, PRDifferException)
        assert issubclass(InvalidURLError, ValidationError)
        assert issubclass(InvalidRepositoryError, ValidationError)
        assert issubclass(InvalidPRNumberError, ValidationError)
        assert issubclass(UnsupportedFormatError, ValidationError)

    def test_github_api_hierarchy(self):
        assert issubclass(GitHubAPIError, PRDifferException)
        assert issubclass(RepositoryNotFoundError, GitHubAPIError)
        assert issubclass(PRNotFoundError, GitHubAPIError)
        assert issubclass(FileNotFoundError, GitHubAPIError)
        assert issubclass(GitHubAuthenticationError, GitHubAPIError)
        assert issubclass(GitHubConnectionError, GitHubAPIError)
        assert issubclass(GitHubRateLimitError, GitHubAPIError)

    def test_cache_hierarchy(self):
        assert issubclass(CacheError, PRDifferException)
        assert issubclass(CacheInvalidationError, CacheError)
        assert issubclass(CacheCorruptionError, CacheError)

    def test_config_hierarchy(self):
        assert issubclass(ConfigurationError, PRDifferException)
        assert issubclass(MissingConfigurationError, ConfigurationError)
        assert issubclass(InvalidConfigurationError, ConfigurationError)
        assert issubclass(SecretsError, ConfigurationError)

    def test_processing_hierarchy(self):
        assert issubclass(ProcessingError, PRDifferException)
        assert issubclass(DiffGenerationError, ProcessingError)
        assert issubclass(FileProcessingError, ProcessingError)
        assert issubclass(PatternMatchingError, ProcessingError)

    def test_resource_hierarchy(self):
        assert issubclass(ResourceError, PRDifferException)
        assert issubclass(ResourceExhaustedError, ResourceError)
        assert issubclass(MemoryLimitError, ResourceError)
        assert issubclass(TimeoutError, ResourceError)

    def test_security_hierarchy(self):
        assert issubclass(SecurityError, PRDifferException)
        assert issubclass(SuspiciousOperationError, SecurityError)
        assert issubclass(InputSanitizationError, SecurityError)
        assert issubclass(SignatureVerificationError, SecurityError)


# ---------------------------------------------------------------------------
# RateLimitError with retry_after
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRateLimitError:
    """Test RateLimitError retry_after field."""

    def test_retry_after_stored(self):
        exc = RateLimitError("too fast", retry_after=60)
        assert exc.retry_after == 60

    def test_retry_after_none(self):
        exc = RateLimitError("too fast")
        assert exc.retry_after is None


# ---------------------------------------------------------------------------
# GitHubAPIError with status_code
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGitHubAPIError:
    """Test GitHubAPIError status_code field."""

    def test_status_code_stored(self):
        exc = GitHubAPIError("fail", status_code=404)
        assert exc.status_code == 404

    def test_status_code_none(self):
        exc = GitHubAPIError("fail")
        assert exc.status_code is None


# ---------------------------------------------------------------------------
# GitLabAPIError with status_code (safe details only)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGitLabAPIError:
    """Test GitLabAPIError preserves safe status/details only."""

    def test_status_code_stored(self):
        from prdiffer.domain.error_codes import E5021_GITLAB_API_ERROR

        exc = GitLabAPIError(
            "GitLab upstream failure",
            status_code=500,
            error_code=E5021_GITLAB_API_ERROR,
            details={"operation": "mergerequests.get"},
        )
        assert isinstance(exc, PRDifferException)
        assert exc.status_code == 500
        assert exc.error_code is E5021_GITLAB_API_ERROR
        assert exc.details == {"operation": "mergerequests.get"}

    def test_never_copies_secret_like_upstream_fields(self):
        from prdiffer.domain.error_codes import E2006_GITLAB_AUTH_FAILED

        # Callers must not pass secrets; constructor stores only what it is given.
        # This test documents the safe allowlist contract: no response_body/token/url.
        exc = GitLabAPIError(
            "GitLab authentication failed",
            status_code=401,
            error_code=E2006_GITLAB_AUTH_FAILED,
            details={"status_code": 401},
        )
        assert "response_body" not in exc.details
        assert "token" not in exc.details
        assert "private_token" not in exc.details
        assert "url" not in exc.details
        assert set(exc.details) == {"status_code"}

        logged = get_exception_details(exc)
        assert logged["status_code"] == 401
        assert "token" not in str(logged["details"])


# ---------------------------------------------------------------------------
# GitHubRateLimitError with retry_after + status_code
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGitHubRateLimitError:
    """Test GitHubRateLimitError with both fields."""

    def test_both_fields_stored(self):
        exc = GitHubRateLimitError("rate limit", retry_after=120, status_code=429)
        assert exc.retry_after == 120
        assert exc.status_code == 429


# ---------------------------------------------------------------------------
# get_exception_details
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetExceptionDetails:
    """Test get_exception_details helper."""

    def test_generic_exception(self):
        exc = ValueError("oops")
        details = get_exception_details(exc)
        assert details["type"] == "ValueError"
        assert details["message"] == "oops"

    def test_prdiffer_exception_includes_details(self):
        exc = PRDifferException("err", details={"foo": "bar"})
        details = get_exception_details(exc)
        assert details["details"] == {"foo": "bar"}

    def test_github_api_error_includes_status_code(self):
        exc = GitHubAPIError("fail", status_code=500)
        details = get_exception_details(exc)
        assert details["status_code"] == 500

    def test_rate_limit_error_includes_retry_after(self):
        exc = RateLimitError("too fast", retry_after=30)
        details = get_exception_details(exc)
        assert details["retry_after"] == 30


# ---------------------------------------------------------------------------
# wrap_github_exception
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWrapGitHubException:
    """Test wrap_github_exception helper."""

    def test_404_repository(self):
        exc = Exception("404: Repository not found")
        wrapped = wrap_github_exception(exc)
        assert isinstance(wrapped, RepositoryNotFoundError)

    def test_404_pull_request(self):
        exc = Exception("404: Pull request not found")
        wrapped = wrap_github_exception(exc)
        assert isinstance(wrapped, PRNotFoundError)

    def test_404_generic(self):
        exc = Exception("404: Not Found")
        wrapped = wrap_github_exception(exc)
        assert isinstance(wrapped, FileNotFoundError)

    def test_401_unauthorized(self):
        exc = Exception("401 Unauthorized")
        wrapped = wrap_github_exception(exc)
        assert isinstance(wrapped, GitHubAuthenticationError)

    def test_403_forbidden(self):
        exc = Exception("403 Forbidden")
        wrapped = wrap_github_exception(exc)
        assert isinstance(wrapped, GitHubAuthenticationError)

    def test_429_rate_limit(self):
        exc = Exception("429 rate limit exceeded")
        wrapped = wrap_github_exception(exc)
        assert isinstance(wrapped, GitHubRateLimitError)
        assert wrapped.retry_after == 60

    def test_rate_limit_keyword(self):
        exc = Exception("API rate limit exceeded")
        wrapped = wrap_github_exception(exc)
        assert isinstance(wrapped, GitHubRateLimitError)

    def test_timeout(self):
        exc = Exception("Connection timeout")
        wrapped = wrap_github_exception(exc)
        assert isinstance(wrapped, GitHubConnectionError)

    def test_connection_error(self):
        exc = Exception("Connection refused")
        wrapped = wrap_github_exception(exc)
        assert isinstance(wrapped, GitHubConnectionError)

    def test_unknown_defaults_to_github_api_error(self):
        exc = Exception("Something completely unknown")
        wrapped = wrap_github_exception(exc)
        assert isinstance(wrapped, GitHubAPIError)
        assert not isinstance(
            wrapped,
            (
                RepositoryNotFoundError,
                PRNotFoundError,
                GitHubAuthenticationError,
                GitHubRateLimitError,
                GitHubConnectionError,
            ),
        )
