"""Unit tests for AuthenticationMiddleware application component.

Tests the AuthenticationMiddleware component which provides API key-based
authentication and authorization functionality.
"""

import os
from unittest.mock import Mock, patch
from ccpragents.application.components.authentication import AuthenticationMiddleware


class TestAuthenticationMiddlewareInitialization:
    """Test suite for AuthenticationMiddleware initialization."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_authentication_initialization_default(self):
        """Test AuthenticationMiddleware initializes with auth disabled."""
        auth = AuthenticationMiddleware()

        assert auth is not None
        assert auth._auth_enabled is False

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "true"})
    def test_authentication_initialization_enabled(self):
        """Test AuthenticationMiddleware initializes with auth enabled."""
        auth = AuthenticationMiddleware()

        assert auth._auth_enabled is True

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "1"})
    def test_authentication_enabled_with_numeric_1(self):
        """Test various ways to enable authentication."""
        auth = AuthenticationMiddleware()

        assert auth._auth_enabled is True

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "yes"})
    def test_authentication_enabled_with_yes(self):
        """Test enabling authentication with 'yes'."""
        auth = AuthenticationMiddleware()

        assert auth._auth_enabled is True

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_authentication_disabled(self):
        """Test authentication is disabled by default."""
        auth = AuthenticationMiddleware()

        assert auth.is_authentication_enabled() is False

    @patch.dict(
        os.environ, {"MCP_AUTH_ENABLED": "true", "MCP_API_KEYS": "key1,key2,key3"}
    )
    def test_authentication_loads_api_keys(self):
        """Test API keys are loaded from environment."""
        auth = AuthenticationMiddleware()

        assert auth.get_configured_api_keys_count() == 3
        assert "key1" in auth._api_keys
        assert "key2" in auth._api_keys
        assert "key3" in auth._api_keys

    @patch.dict(
        os.environ, {"MCP_AUTH_ENABLED": "true", "MCP_API_KEYS": "key1 , key2 , key3 "}
    )
    def test_authentication_trims_whitespace(self):
        """Test API keys are trimmed of whitespace."""
        auth = AuthenticationMiddleware()

        assert auth.get_configured_api_keys_count() == 3
        assert "key1" in auth._api_keys
        assert "key2" in auth._api_keys
        assert "key3" in auth._api_keys

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "true", "MCP_API_KEYS": ""})
    def test_authentication_empty_api_keys(self):
        """Test empty API keys string."""
        auth = AuthenticationMiddleware()

        assert auth.get_configured_api_keys_count() == 0

    @patch.dict(
        os.environ,
        {"MCP_AUTH_ENABLED": "true", "MCP_ADMIN_API_KEY": "admin_secret_123"},
    )
    def test_authentication_admin_key_loaded(self):
        """Test admin API key is loaded."""
        auth = AuthenticationMiddleware()

        assert auth._admin_api_key_hash is not None
        assert auth._admin_api_key_hash == auth._hash_api_key("admin_secret_123")

    def test_authentication_with_logger(self):
        """Test AuthenticationMiddleware with custom logger."""
        mock_logger = Mock()
        with patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"}):
            auth = AuthenticationMiddleware(logger=mock_logger)

        assert auth._logger == mock_logger


class TestAuthenticationMiddlewareHashApiKey:
    """Test suite for _hash_api_key method."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_hash_api_key_consistent(self):
        """Test hashing produces consistent results."""
        auth = AuthenticationMiddleware()

        hash1 = auth._hash_api_key("test_key")
        hash2 = auth._hash_api_key("test_key")

        assert hash1 == hash2

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_hash_api_key_different(self):
        """Test different keys produce different hashes."""
        auth = AuthenticationMiddleware()

        hash1 = auth._hash_api_key("test_key_1")
        hash2 = auth._hash_api_key("test_key_2")

        assert hash1 != hash2

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_hash_api_key_sha256_length(self):
        """Test SHA-256 produces 64 character hex string."""
        auth = AuthenticationMiddleware()

        hash_result = auth._hash_api_key("test_key")

        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)


class TestAuthenticationMiddlewareAuthenticate:
    """Test suite for authenticate method."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_authenticate_disabled_allows_all(self):
        """Test authentication disabled allows all requests."""
        auth = AuthenticationMiddleware()

        is_auth, client_id = auth.authenticate(None)

        assert is_auth is True
        assert client_id == "anonymous"

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "true"})
    def test_authenticate_enabled_no_key_fails(self):
        """Test authentication fails when no key provided."""
        auth = AuthenticationMiddleware()

        is_auth, client_id = auth.authenticate(None)

        assert is_auth is False
        assert client_id is None

    @patch.dict(
        os.environ, {"MCP_AUTH_ENABLED": "true", "MCP_API_KEYS": "test_key_123"}
    )
    def test_authenticate_valid_key_succeeds(self):
        """Test authentication succeeds with valid key."""
        auth = AuthenticationMiddleware()

        is_auth, client_id = auth.authenticate("test_key_123")

        assert is_auth is True
        assert client_id is not None
        assert client_id.startswith("api_key_")

    @patch.dict(
        os.environ, {"MCP_AUTH_ENABLED": "true", "MCP_API_KEYS": "test_key_123"}
    )
    def test_authenticate_invalid_key_fails(self):
        """Test authentication fails with invalid key."""
        auth = AuthenticationMiddleware()

        is_auth, client_id = auth.authenticate("wrong_key")

        assert is_auth is False
        assert client_id is None

    @patch.dict(
        os.environ, {"MCP_AUTH_ENABLED": "true", "MCP_ADMIN_API_KEY": "admin_secret"}
    )
    def test_authenticate_admin_key(self):
        """Test admin API key authentication."""
        auth = AuthenticationMiddleware()

        is_auth, client_id = auth.authenticate("admin_secret")

        assert is_auth is True
        assert client_id == "admin"

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "true", "MCP_API_KEYS": "key1,key2"})
    def test_authenticate_multiple_keys(self):
        """Test authentication with multiple valid keys."""
        auth = AuthenticationMiddleware()

        is_auth1, client_id1 = auth.authenticate("key1")
        is_auth2, client_id2 = auth.authenticate("key2")

        assert is_auth1 is True
        assert is_auth2 is True
        assert client_id1 != client_id2  # Different client IDs for different keys


class TestAuthenticationMiddlewareExtractClientIdentifier:
    """Test suite for extract_client_identifier method."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_extract_x_api_key_header(self):
        """Test extracting API key from X-API-Key header."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier({"x-api-key": "test_key"})

        assert api_key == "test_key"
        assert client_id is None

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_extract_x_api_key_header_capitalized(self):
        """Test extracting API key from X-API-Key header (capitalized)."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier({"X-API-Key": "test_key"})

        assert api_key == "test_key"
        assert client_id is None

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_extract_authorization_bearer_header(self):
        """Test extracting API key from Authorization Bearer header."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier(
            {"authorization": "Bearer test_token"}
        )

        assert api_key == "test_token"
        assert client_id is None

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_extract_authorization_bearer_header_capitalized(self):
        """Test extracting API key from Authorization Bearer header (capitalized)."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier(
            {"Authorization": "Bearer test_token"}
        )

        assert api_key == "test_token"
        assert client_id is None

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_extract_x_forwarded_for_header(self):
        """Test extracting IP from X-Forwarded-For header."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier(
            {"x-forwarded-for": "192.168.1.1"}
        )

        assert api_key is None
        assert client_id == "192.168.1.1"

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_extract_x_real_ip_header(self):
        """Test extracting IP from X-Real-IP header."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier({"x-real-ip": "10.0.0.1"})

        assert api_key is None
        assert client_id == "10.0.0.1"

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_extract_x_forwarded_for_multiple_ips(self):
        """Test extracting first IP from X-Forwarded-For with multiple IPs."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier(
            {"x-forwarded-for": "192.168.1.1, 10.0.0.1, 172.16.0.1"}
        )

        assert api_key is None
        assert client_id == "192.168.1.1"

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_extract_no_identifier(self):
        """Test when no identifier is found."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier({})

        assert api_key is None
        assert client_id is None

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_extract_api_key_priority_over_ip(self):
        """Test API key takes priority over IP address."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier(
            {"x-api-key": "test_key", "x-forwarded-for": "192.168.1.1"}
        )

        assert api_key == "test_key"
        assert client_id is None


class TestAuthenticationMiddlewareValidateApiKeyFormat:
    """Test suite for validate_api_key_format method."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_validate_valid_api_key(self):
        """Test validation of valid API key."""
        auth = AuthenticationMiddleware()

        assert auth.validate_api_key_format("a" * 32) is True

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_validate_too_short(self):
        """Test validation rejects keys that are too short."""
        auth = AuthenticationMiddleware()

        assert auth.validate_api_key_format("short") is False

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_validate_too_long(self):
        """Test validation rejects keys that are too long."""
        auth = AuthenticationMiddleware()

        assert auth.validate_api_key_format("a" * 300) is False

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_validate_empty_key(self):
        """Test validation rejects empty key."""
        auth = AuthenticationMiddleware()

        assert auth.validate_api_key_format("") is False

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_validate_non_ascii(self):
        """Test validation rejects non-ASCII characters."""
        auth = AuthenticationMiddleware()

        assert auth.validate_api_key_format("test_测试") is False

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_validate_non_printable(self):
        """Test validation rejects non-printable characters."""
        auth = AuthenticationMiddleware()

        assert auth.validate_api_key_format("test\x00key") is False

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_validate_exactly_16_chars(self):
        """Test validation accepts exactly 16 characters."""
        auth = AuthenticationMiddleware()

        assert auth.validate_api_key_format("a" * 16) is True

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_validate_exactly_256_chars(self):
        """Test validation accepts exactly 256 characters."""
        auth = AuthenticationMiddleware()

        assert auth.validate_api_key_format("a" * 256) is True


class TestAuthenticationMiddlewareAddApiKey:
    """Test suite for add_api_key method."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_add_api_key_valid(self):
        """Test adding a valid API key."""
        auth = AuthenticationMiddleware()

        result = auth.add_api_key("new_key_12345678")

        assert result is True
        assert "new_key_12345678" in auth._api_keys

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_add_api_key_invalid_format(self):
        """Test adding an invalid format API key fails."""
        auth = AuthenticationMiddleware()

        result = auth.add_api_key("short")

        assert result is False

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_add_api_key_duplicate(self):
        """Test adding duplicate API key fails."""
        auth = AuthenticationMiddleware()
        auth.add_api_key("test_key_12345678")

        result = auth.add_api_key("test_key_12345678")

        assert result is False


class TestAuthenticationMiddlewareRemoveApiKey:
    """Test suite for remove_api_key method."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_remove_api_key_existing(self):
        """Test removing an existing API key."""
        auth = AuthenticationMiddleware()
        auth.add_api_key("test_key_12345678")

        result = auth.remove_api_key("test_key_12345678")

        assert result is True
        assert "test_key_12345678" not in auth._api_keys

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_remove_api_key_nonexistent(self):
        """Test removing a non-existent API key fails."""
        auth = AuthenticationMiddleware()

        result = auth.remove_api_key("nonexistent_key")

        assert result is False


class TestAuthenticationMiddlewareGetConfiguredApiKeysCount:
    """Test suite for get_configured_api_keys_count method."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_get_count_empty(self):
        """Test count when no keys configured."""
        auth = AuthenticationMiddleware()

        assert auth.get_configured_api_keys_count() == 0

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_get_count_with_keys(self):
        """Test count with keys configured."""
        auth = AuthenticationMiddleware()
        auth.add_api_key("key1_123456789012")
        auth.add_api_key("key2_123456789012")

        assert auth.get_configured_api_keys_count() == 2


class TestAuthenticationMiddlewareGetStatus:
    """Test suite for get_status method."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_get_status_disabled(self):
        """Test status when authentication disabled."""
        auth = AuthenticationMiddleware()

        status = auth.get_status()

        assert status["authentication_enabled"] is False
        assert status["api_keys_configured"] == 0
        assert status["admin_api_key_configured"] is False
        assert status["default_client_id"] == "anonymous"

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "true", "MCP_API_KEYS": "key1,key2"})
    def test_get_status_enabled_with_keys(self):
        """Test status when enabled with keys."""
        auth = AuthenticationMiddleware()

        status = auth.get_status()

        assert status["authentication_enabled"] is True
        assert status["api_keys_configured"] == 2

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "true", "MCP_ADMIN_API_KEY": "admin"})
    def test_get_status_with_admin(self):
        """Test status with admin key configured."""
        auth = AuthenticationMiddleware()

        status = auth.get_status()

        assert status["admin_api_key_configured"] is True


class TestAuthenticationMiddlewareProtocolCompliance:
    """Test suite for AuthenticationMiddleware protocol compliance."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_has_required_methods(self):
        """Test that AuthenticationMiddleware has all required protocol methods."""
        auth = AuthenticationMiddleware()

        # Check all required methods exist
        assert hasattr(auth, "authenticate")
        assert callable(auth.authenticate)
        assert hasattr(auth, "extract_client_identifier")
        assert callable(auth.extract_client_identifier)
        assert hasattr(auth, "is_authentication_enabled")
        assert callable(auth.is_authentication_enabled)
        assert hasattr(auth, "get_status")
        assert callable(auth.get_status)


class TestAuthenticationMiddlewareEdgeCases:
    """Test suite for AuthenticationMiddleware edge cases."""

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_authenticate_empty_string(self):
        """Test authenticating with empty string."""
        auth = AuthenticationMiddleware()

        is_auth, client_id = auth.authenticate("")

        assert is_auth is True  # Disabled, so allows all
        assert client_id == "anonymous"

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "true"})
    def test_authenticate_empty_string_enabled(self):
        """Test authenticating with empty string when enabled."""
        auth = AuthenticationMiddleware()

        is_auth, client_id = auth.authenticate("")

        assert is_auth is False
        assert client_id is None

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_authorization_header_without_bearer(self):
        """Test Authorization header without Bearer prefix."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier(
            {"authorization": "InvalidFormat token"}
        )

        assert api_key is None
        # Falls back to IP if available
        assert client_id is None

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "false"})
    def test_bearer_with_empty_token(self):
        """Test Bearer header with empty token results in no key."""
        auth = AuthenticationMiddleware()

        api_key, client_id = auth.extract_client_identifier(
            {"authorization": "Bearer "}
        )

        # Empty string after "Bearer " is falsy, so api_key is None
        assert api_key is None
        assert client_id is None

    @patch.dict(os.environ, {"MCP_AUTH_ENABLED": "true"})
    def test_case_sensitive_api_keys(self):
        """Test API key comparison is case-sensitive."""
        auth = AuthenticationMiddleware()
        auth.add_api_key("TestKey1234567890")

        is_auth, _ = auth.authenticate("testkey1234567890")  # Lowercase

        assert is_auth is False
