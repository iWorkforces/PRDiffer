"""Authentication component for API key-based access control.

This component provides authentication and authorization functionality
for the MCP server, supporting API key-based access control with
per-client rate limiting integration.
"""

import hashlib
import os
import logging
from typing import Dict, Any, Tuple, Optional, Set

from ..interfaces.protocols import AuthenticationProtocol


class AuthenticationMiddleware(AuthenticationProtocol):
    """Component responsible for authentication and authorization.

    Features:
    - API key-based authentication
    - Per-client rate limiting support
    - Configuration-based enable/disable
    - Multiple API key support
    - Client identifier extraction for rate limiting
    """

    def __init__(self, logger: Optional[Any] = None):
        """Initialize authentication middleware.

        Args:
            logger: Optional logger instance
        """
        self._logger = logger or logging.getLogger(__name__)

        # Load configuration from environment
        self._auth_enabled = os.getenv("MCP_AUTH_ENABLED", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        self._api_keys_env = os.getenv("MCP_API_KEYS", "")

        # Parse API keys from environment (comma-separated)
        self._api_keys: Set[str] = set()
        if self._api_keys_env:
            self._api_keys = set(
                key.strip() for key in self._api_keys_env.split(",") if key.strip()
            )

        # Hash API keys for secure comparison
        self._hashed_api_keys: Set[str] = set()
        for key in self._api_keys:
            self._hashed_api_keys.add(self._hash_api_key(key))

        # Admin API key (if provided)
        self._admin_api_key_hash: Optional[str] = None
        admin_key = os.getenv("MCP_ADMIN_API_KEY", "")
        if admin_key:
            self._admin_api_key_hash = self._hash_api_key(admin_key)

        # Default client ID for unauthenticated requests
        self._default_client_id = "anonymous"

        self._logger.info(
            "Authentication middleware initialized",
            extra={
                "enabled": self._auth_enabled,
                "api_keys_configured": len(self._api_keys),
                "admin_configured": self._admin_api_key_hash is not None,
            },
        )

    def _hash_api_key(self, api_key: str) -> str:
        """Hash an API key for secure storage and comparison.

        Uses SHA-256 for cryptographic security. The hash is used
        to avoid storing plain-text API keys in memory.

        Args:
            api_key: The API key to hash

        Returns:
            Hex-encoded SHA-256 hash of the API key
        """
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    def authenticate(self, api_key: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Authenticate a request using API key.

        Args:
            api_key: The API key to validate (may be None for unauthenticated requests)

        Returns:
            Tuple of (is_authenticated, client_id) where:
            - is_authenticated: True if authentication succeeded
            - client_id: Client identifier for rate limiting (None if not authenticated)
        """
        # If authentication is disabled, allow all requests
        if not self._auth_enabled:
            return True, self._default_client_id

        # No API key provided
        if not api_key:
            self._logger.warning(
                "Authentication failed: No API key provided",
            )
            return False, None

        # Hash the provided API key for comparison
        provided_hash = self._hash_api_key(api_key)

        # Check admin API key first
        if self._admin_api_key_hash and provided_hash == self._admin_api_key_hash:
            self._logger.debug(
                "Admin authentication successful",
            )
            return True, "admin"

        # Check regular API keys
        if provided_hash in self._hashed_api_keys:
            # Use a truncated hash as client ID for rate limiting
            client_id = f"api_key_{provided_hash[:16]}"
            self._logger.debug(
                "API key authentication successful",
                extra={"client_id": client_id},
            )
            return True, client_id

        self._logger.warning("Authentication failed: Invalid API key")
        return False, None

    def extract_client_identifier(
        self, headers: Dict[str, str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract client identifier from request headers.

        This method extracts API keys from various header sources:
        - X-API-Key: Standard API key header
        - Authorization: Bearer token format

        For fallback, it uses the X-Forwarded-For or X-Real-IP headers
        to get the client IP address.

        Args:
            headers: Request headers dictionary

        Returns:
            Tuple of (api_key, client_id) where:
            - api_key: The extracted API key (or None if not present)
            - client_id: The client identifier for rate limiting (IP or API key hash)
        """
        # Try X-API-Key header first
        api_key = headers.get("x-api-key") or headers.get("X-API-Key")

        # Try Authorization header with Bearer token
        if not api_key:
            auth_header = headers.get("authorization") or headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header[7:]  # Remove "Bearer " prefix

        # Extract IP address for fallback
        client_ip = (
            headers.get("x-forwarded-for")
            or headers.get("X-Forwarded-For")
            or headers.get("x-real-ip")
            or headers.get("X-Real-IP")
        )

        # If X-Forwarded-For contains multiple IPs, take the first one
        if client_ip and "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        # Determine client ID based on what we have
        if api_key:
            # We have an API key, use it (will be hashed in authenticate())
            return api_key, None  # authenticate() will hash it
        elif client_ip:
            # No API key, use IP as client ID
            return None, client_ip
        else:
            # No identifier found
            return None, None

    def is_authentication_enabled(self) -> bool:
        """Check if authentication is enabled.

        Returns:
            True if authentication is required
        """
        return self._auth_enabled

    def validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format before attempting authentication.

        This method provides basic validation to reject obviously invalid
        API keys before attempting authentication.

        Args:
            api_key: The API key to validate

        Returns:
            True if the API key format is valid
        """
        # Basic format validation
        if not api_key:
            return False

        # Check length (API keys should be between 16 and 256 characters)
        if len(api_key) < 16 or len(api_key) > 256:
            return False

        # Check for printable ASCII characters
        if not api_key.isascii() or not api_key.isprintable():
            return False

        return True

    def add_api_key(self, api_key: str) -> bool:
        """Add a new API key to the valid keys set.

        This method allows runtime addition of API keys.

        Args:
            api_key: The API key to add

        Returns:
            True if the API key was added successfully
        """
        if not self.validate_api_key_format(api_key):
            self._logger.warning("Failed to add API key: Invalid format")
            return False

        api_key_hash = self._hash_api_key(api_key)
        if api_key_hash in self._hashed_api_keys:
            self._logger.warning("API key already exists")
            return False

        self._hashed_api_keys.add(api_key_hash)
        self._api_keys.add(api_key)
        self._logger.info("API key added successfully")
        return True

    def remove_api_key(self, api_key: str) -> bool:
        """Remove an API key from the valid keys set.

        Args:
            api_key: The API key to remove

        Returns:
            True if the API key was removed successfully
        """
        api_key_hash = self._hash_api_key(api_key)
        if api_key_hash in self._hashed_api_keys:
            self._hashed_api_keys.remove(api_key_hash)
            self._api_keys.discard(api_key)
            self._logger.info("API key removed successfully")
            return True
        return False

    def get_configured_api_keys_count(self) -> int:
        """Get the number of configured API keys.

        Returns:
            Number of configured API keys
        """
        return len(self._api_keys)

    def get_status(self) -> Dict[str, Any]:
        """Get authentication status and configuration.

        Returns:
            Dictionary containing authentication status
        """
        return {
            "authentication_enabled": self._auth_enabled,
            "api_keys_configured": len(self._api_keys),
            "admin_api_key_configured": self._admin_api_key_hash is not None,
            "default_client_id": self._default_client_id,
        }
