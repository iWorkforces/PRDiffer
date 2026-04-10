"""Tests for structured error codes and MCPError hierarchy."""

import builtins

import pytest

from prdiffer.domain.errors import (
    ErrorCategory,
    ErrorCode,
    MCPError,
    InputValidationError,
    AuthenticationError,
    RateLimitError,
    ResourceNotFoundError,
    InternalServerError,
    get_error_for_exception,
    create_error_response,
)
from prdiffer.domain.error_codes import (
    E1001_INVALID_URL,
    E2002_AUTH_FAILED,
    E3001_RATE_LIMITED,
    E4001_REPO_NOT_FOUND,
    E5001_INTERNAL_ERROR,
    E5002_GITHUB_API_ERROR,
)


# ---------------------------------------------------------------------------
# ErrorCategory
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_all_categories(self):
        assert ErrorCategory.INPUT_VALIDATION == "1"
        assert ErrorCategory.AUTHENTICATION == "2"
        assert ErrorCategory.RATE_LIMITING == "3"
        assert ErrorCategory.NOT_FOUND == "4"
        assert ErrorCategory.INTERNAL == "5"

    def test_is_str_enum(self):
        assert isinstance(ErrorCategory.INPUT_VALIDATION, str)


# ---------------------------------------------------------------------------
# ErrorCode
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestErrorCode:
    """Test ErrorCode frozen dataclass."""

    def test_create_error_code(self):
        code = ErrorCode(
            code="E9999",
            name="TEST",
            message="test msg",
            remediation="fix it",
            category=ErrorCategory.INTERNAL,
        )
        assert code.code == "E9999"
        assert code.name == "TEST"
        assert code.message == "test msg"
        assert code.remediation == "fix it"

    def test_str_format(self):
        code = ErrorCode(
            code="E1001",
            name="INVALID_URL",
            message="bad",
            remediation="fix",
            category=ErrorCategory.INPUT_VALIDATION,
        )
        assert str(code) == "E1001_INVALID_URL"

    def test_to_dict(self):
        code = ErrorCode(
            code="E1001",
            name="INVALID_URL",
            message="bad url",
            remediation="use valid url",
            category=ErrorCategory.INPUT_VALIDATION,
        )
        d = code.to_dict()
        assert d["error_code"] == "E1001_INVALID_URL"
        assert d["message"] == "bad url"
        assert d["remediation"] == "use valid url"
        assert d["category"] == "INPUT_VALIDATION"

    def test_frozen_immutable(self):
        code = E1001_INVALID_URL
        with pytest.raises(AttributeError):
            setattr(code, "code", "E9999")

    def test_predefined_constants(self):
        assert E1001_INVALID_URL.code == "E1001"
        assert E5001_INTERNAL_ERROR.code == "E5001"
        assert E5001_INTERNAL_ERROR.category == ErrorCategory.INTERNAL


# ---------------------------------------------------------------------------
# MCPError
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMCPError:
    """Test MCPError base exception."""

    def test_create_mcp_error(self):
        exc = MCPError(E1001_INVALID_URL)
        assert exc.error_code is E1001_INVALID_URL
        assert exc.detail is None
        assert exc.context == {}

    def test_with_detail_and_context(self):
        exc = MCPError(E1001_INVALID_URL, detail="bad url", context={"url": "x"})
        assert exc.detail == "bad url"
        assert exc.context == {"url": "x"}

    def test_to_dict_basic(self):
        exc = MCPError(E1001_INVALID_URL)
        d = exc.to_dict()
        assert d["error_code"] == "E1001_INVALID_URL"
        assert "detail" not in d

    def test_to_dict_with_detail(self):
        exc = MCPError(E1001_INVALID_URL, detail="oops")
        d = exc.to_dict()
        assert d["detail"] == "oops"

    def test_to_dict_with_context(self):
        exc = MCPError(E1001_INVALID_URL, context={"k": "v"})
        d = exc.to_dict()
        assert d["context"] == {"k": "v"}

    def test_str_representation(self):
        exc = MCPError(E1001_INVALID_URL)
        assert "E1001" in str(exc)


# ---------------------------------------------------------------------------
# MCPError subclasses
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMCPErrorSubclasses:
    """Test MCPError subclass hierarchy."""

    def test_input_validation_error(self):
        exc = InputValidationError(E1001_INVALID_URL)
        assert isinstance(exc, MCPError)

    def test_authentication_error(self):
        exc = AuthenticationError(E2002_AUTH_FAILED)
        assert isinstance(exc, MCPError)

    def test_rate_limit_error(self):
        exc = RateLimitError(E3001_RATE_LIMITED)
        assert isinstance(exc, MCPError)

    def test_resource_not_found_error(self):
        exc = ResourceNotFoundError(E4001_REPO_NOT_FOUND)
        assert isinstance(exc, MCPError)

    def test_internal_server_error(self):
        exc = InternalServerError(E5001_INTERNAL_ERROR)
        assert isinstance(exc, MCPError)


# ---------------------------------------------------------------------------
# get_error_for_exception
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetErrorForException:
    """Test exception-to-error-code mapping."""

    def test_unknown_exception_maps_to_internal(self):
        code = get_error_for_exception(RuntimeError("boom"))
        assert code is E5001_INTERNAL_ERROR

    def test_timeout_maps_to_timeout(self):
        from prdiffer.domain.error_codes import E5004_TIMEOUT_ERROR

        code = get_error_for_exception(builtins_timeout_error())
        assert code is E5004_TIMEOUT_ERROR

    def test_value_error_maps_to_invalid_url(self):
        code = get_error_for_exception(ValueError("bad"))
        assert code is E1001_INVALID_URL

    def test_connection_error_maps_to_github_api(self):
        code = get_error_for_exception(ConnectionError("refused"))
        assert code is E5002_GITHUB_API_ERROR


def builtins_timeout_error():
    """Create a builtin TimeoutError (not the domain one)."""
    return builtins.TimeoutError("timed out")


# ---------------------------------------------------------------------------
# create_error_response
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateErrorResponse:
    """Test create_error_response utility."""

    def test_basic_response(self):
        resp = create_error_response(E1001_INVALID_URL)
        assert resp["success"] is False
        assert resp["error"]["error_code"] == "E1001_INVALID_URL"

    def test_with_detail(self):
        resp = create_error_response(E1001_INVALID_URL, detail="bad url")
        assert resp["error"]["detail"] == "bad url"

    def test_with_context(self):
        resp = create_error_response(E1001_INVALID_URL, context={"url": "foo"})
        assert resp["error"]["context"] == {"url": "foo"}

    def test_without_detail_no_key(self):
        resp = create_error_response(E1001_INVALID_URL)
        assert "detail" not in resp["error"]

    def test_without_context_no_key(self):
        resp = create_error_response(E1001_INVALID_URL)
        assert "context" not in resp["error"]
