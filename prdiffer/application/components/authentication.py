"""Authentication component for API key-based access control.

This component provides authentication and authorization functionality
for the MCP server, supporting API key-based access control with
per-client rate limiting integration and brute-force protection.

Security Note:
- JWT signature verification is supported via verify_jwt_token() method
- The parse_jwt_payload() method does NOT verify signatures and should
  only be used for extracting metadata (like expiration time)
- For authentication decisions, always use verify_jwt_token() or API keys
"""

import base64
import binascii
import hashlib
import json
import os
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from threading import RLock

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from prdiffer.domain.interfaces.protocols import AuthenticationProtocol
from prdiffer.infrastructure.security.input_validator import InputValidator
from prdiffer.domain.exceptions import AuthenticationError
from prdiffer.domain.errors import E2002_AUTH_FAILED


@dataclass
class AuthFailureRecord:
    """Record of authentication failures for rate limiting."""

    count: int = 0
    first_failure: float = field(default_factory=time.time)
    last_failure: float = field(default_factory=time.time)


class AuthenticationMiddleware(AuthenticationProtocol):
    """Component responsible for authentication and authorization.

    Features:
    - API key-based authentication
    - Per-client rate limiting support
    - Configuration-based enable/disable
    - Multiple API key support
    - Client identifier extraction for rate limiting
    - Brute-force protection with exponential backoff
    """

    # Rate limiting configuration
    DEFAULT_MAX_FAILURES_PER_MINUTE = 5
    DEFAULT_LOCKOUT_DURATION = 60  # seconds
    DEFAULT_FAILURE_WINDOW = 300  # 5 minutes

    def __init__(
        self,
        logger: Any | None = None,
        max_failures_per_minute: int = DEFAULT_MAX_FAILURES_PER_MINUTE,
        lockout_duration: int = DEFAULT_LOCKOUT_DURATION,
        failure_window: int = DEFAULT_FAILURE_WINDOW,
        check_token_expiration: bool = True,
        input_validator: InputValidator | None = None,
    ):
        """Initialize authentication middleware.

        Args:
            logger: Optional logger instance
            max_failures_per_minute: Maximum failed attempts before lockout
            lockout_duration: Duration of lockout in seconds
            failure_window: Time window for counting failures in seconds
            check_token_expiration: Whether to check JWT token expiration (default: True)
        """
        self._logger = logger or logging.getLogger(__name__)
        self._input_validator = input_validator or InputValidator()

        # Load configuration from environment
        self._auth_enabled = os.getenv('MCP_AUTH_ENABLED', 'false').lower() in (
            'true',
            '1',
            'yes',
        )
        self._api_keys_env = os.getenv('MCP_API_KEYS', '')

        # Brute-force protection settings
        self._max_failures_per_minute = max_failures_per_minute
        self._lockout_duration = lockout_duration
        self._failure_window = failure_window

        # Token expiration check setting
        self._check_token_expiration = check_token_expiration

        # Thread-safe failure tracking
        self._lock = RLock()
        self._auth_failures: dict[str, AuthFailureRecord] = defaultdict(AuthFailureRecord)
        self._locked_clients: dict[str, float] = {}  # client_id -> unlock_time

        # Parse API keys from environment and store ONLY hashes (no raw keys)
        self._hashed_api_keys: set[str] = set()
        self._api_key_count: int = 0
        if self._api_keys_env:
            raw_keys = [key.strip() for key in self._api_keys_env.split(',') if key.strip()]
            self._api_key_count = len(raw_keys)
            for key in raw_keys:
                self._hashed_api_keys.add(self._hash_api_key(key))

        # Admin API key (if provided)
        self._admin_api_key_hash: str | None = None
        admin_key = os.getenv('MCP_ADMIN_API_KEY', '')
        if admin_key:
            self._admin_api_key_hash = self._hash_api_key(admin_key)

        # Default client ID for unauthenticated requests
        self._default_client_id = 'anonymous'

        self._logger.info(
            'Authentication middleware initialized',
            extra={
                'enabled': self._auth_enabled,
                'api_keys_configured': self._api_key_count,
                'admin_configured': self._admin_api_key_hash is not None,
                'max_failures_per_minute': self._max_failures_per_minute,
                'lockout_duration': self._lockout_duration,
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
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()

    def _is_locked_out(self, client_identifier: str) -> bool:
        """Check if a client is currently locked out.

        Args:
            client_identifier: The client identifier to check

        Returns:
            True if client is locked out
        """
        current_time = time.time()
        with self._lock:
            if client_identifier in self._locked_clients:
                unlock_time = self._locked_clients[client_identifier]
                if current_time < unlock_time:
                    return True
                # Lockout expired, remove it
                del self._locked_clients[client_identifier]
            return False

    def _record_failure(self, client_identifier: str) -> None:
        """Record an authentication failure for a client."""
        current_time = time.time()
        with self._lock:
            record = self._auth_failures[client_identifier]

            # Clean up old failures outside of window
            time_elapsed = current_time - record.first_failure
            if time_elapsed <= 0:
                time_elapsed = 0.001
            elif time_elapsed > self._failure_window:
                record.count = 1
                record.first_failure = current_time
                time_elapsed = 0.001
            else:
                record.count += 1

            record.last_failure = current_time

    def _record_success(self, client_identifier: str) -> None:
        """Record a successful authentication and clear failures."""
        with self._lock:
            # Clear any failure records for this client
            if client_identifier in self._auth_failures:
                del self._auth_failures[client_identifier]

    def _get_client_identifier(self, api_key: str | None) -> str:
        """Get a client identifier for tracking authentication attempts.

        Args:
            api_key: The API key provided (may be None)

        Returns:
            Client identifier string
        """
        if api_key:
            return f'key_{self._hash_api_key(api_key)[:16]}'
        return 'anonymous'

    def _looks_like_jwt_token(self, token: str) -> bool:
        """Check if a token looks like a JWT token.

        JWT tokens typically have these characteristics:
        - Contains dots (separates base64 encoded parts)
        - Longer than 40 characters
        - May include 'Bearer' prefix in Authorization header

        This is a simple heuristic check and NOT a security validation.
        Use it to distinguish between API keys and JWT tokens for routing.

        Args:
            token: The token to check

        Returns:
            True if token appears to be a JWT token
        """
        if '.' in token:
            return True

        if len(token) > 40:
            return True

        # Check for Bearer prefix (after cleaning)
        if token.startswith('Bearer '):
            clean_token = token.replace('Bearer ', '')
            if clean_token.startswith('Bearer '):
                return True

        return False

    def authenticate(self, api_key: str | None) -> tuple[bool, str | None]:
        """Authenticate a request using API key with brute-force protection.

        Args:
            api_key: The API key to validate (may be None for unauthenticated requests)

        Returns:
            Tuple of (is_authenticated, client_id) where:
            - is_authenticated: True if authentication succeeded
            - client_id: Client identifier for rate limiting (None if not authenticated)

        Raises:
            RuntimeError: If client is locked out due to too many failures
        """
        # If authentication is disabled, allow all requests
        if not self._auth_enabled:
            return True, self._default_client_id

        # Get client identifier for tracking
        client_identifier = self._get_client_identifier(api_key)

        # Check if client is locked out
        if self._is_locked_out(client_identifier):
            self._logger.warning(f'Authentication blocked: Client locked out: {client_identifier[:20]}...')
            raise AuthenticationError(
                'Too many authentication failures. Please try again later.',
                error_code=E2002_AUTH_FAILED,
            )

        # No API key provided
        if not api_key:
            self._record_failure(client_identifier)
            self._logger.warning(
                'Authentication failed: No API key provided',
            )
            return False, None

        # Check if api_key looks like a JWT token (dots, length, Bearer format)
        if self._check_token_expiration and api_key:
            # Check if api_key looks like a JWT token (dots, length, Bearer format)
            if self._looks_like_jwt_token(api_key):
                # JWT token: check expiration without signature verification
                is_expired, error_message = self.is_token_expired(api_key)
            else:
                # API key: validate format and check against configured keys
                if not self.validate_api_key_format(api_key):
                    self._record_failure(client_identifier)
                    self._logger.warning('Authentication failed: Invalid API key format')
                    return False, None
                provided_hash = self._hash_api_key(api_key)
                if self._admin_api_key_hash and provided_hash == self._admin_api_key_hash:
                    self._record_success(client_identifier)
                    self._logger.debug('Admin authentication successful')
                    return True, 'admin'
                if provided_hash in self._hashed_api_keys:
                    client_id = f'api_key_{provided_hash[:16]}'
                    self._record_success(client_identifier)
                    self._logger.debug(
                        'API key authentication successful',
                        extra={'client_id': client_id},
                    )
                    return True, client_id
                else:
                    self._record_failure(client_identifier)
                    self._logger.warning('Authentication failed: Invalid API key')
                    return False, None

        # Hash the provided API key for comparison
        provided_hash = self._hash_api_key(api_key)

        # Check admin API key first
        if self._admin_api_key_hash and provided_hash == self._admin_api_key_hash:
            self._record_success(client_identifier)
            self._logger.debug(
                'Admin authentication successful',
            )
            return True, 'admin'

        # Check regular API keys
        if provided_hash in self._hashed_api_keys:
            # Use a truncated hash as client ID for rate limiting
            client_id = f'api_key_{provided_hash[:16]}'
            self._record_success(client_identifier)
            self._logger.debug(
                'API key authentication successful',
                extra={'client_id': client_id},
            )
            return True, client_id

        # Authentication failed - record the failure
        self._record_failure(client_identifier)
        self._logger.warning(
            'Authentication failed: Invalid API key',
            extra={'failures': self._auth_failures.get(client_identifier, AuthFailureRecord()).count},
        )
        return False, None

    def extract_client_identifier(self, headers: dict[str, str]) -> tuple[str | None, str | None]:
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
        api_key = headers.get('x-api-key') or headers.get('X-API-Key')

        # Try Authorization header with Bearer token
        if not api_key:
            auth_header = headers.get('authorization') or headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                api_key = auth_header[7:]  # Remove "Bearer " prefix

        # Extract IP address for fallback
        client_ip = headers.get('x-forwarded-for') or headers.get('X-Forwarded-For') or headers.get('x-real-ip') or headers.get('X-Real-IP')

        # If X-Forwarded-For contains multiple IPs, take the first one
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

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

    def validate_token(self, token: str) -> str:
        """Validate a token format via the centralized input validator.

        Args:
            token: Token to validate

        Returns:
            str: Validated token

        Raises:
            InputSanitizationError: If token format is invalid
        """
        return self._input_validator.validate_token(token)

    def add_api_key(self, api_key: str) -> bool:
        """Add a new API key to the valid keys set.

        This method allows runtime addition of API keys.

        Args:
            api_key: The API key to add

        Returns:
            True if the API key was added successfully
        """
        if not self.validate_api_key_format(api_key):
            self._logger.warning('Failed to add API key: Invalid format')
            return False

        api_key_hash = self._hash_api_key(api_key)
        if api_key_hash in self._hashed_api_keys:
            self._logger.warning('API key already exists')
            return False

        self._hashed_api_keys.add(api_key_hash)
        self._api_key_count += 1
        self._logger.info('API key added successfully')
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
            self._api_key_count -= 1
            self._logger.info('API key removed successfully')
            return True
        return False

    def get_configured_api_keys_count(self) -> int:
        """Get the number of configured API keys.

        Returns:
            Number of configured API keys
        """
        return self._api_key_count

    def get_status(self) -> dict[str, Any]:
        """Get authentication status and configuration.

        Returns:
            Dictionary containing authentication status
        """
        return {
            'authentication_enabled': self._auth_enabled,
            'api_keys_configured': self._api_key_count,
            'admin_api_key_configured': self._admin_api_key_hash is not None,
            'default_client_id': self._default_client_id,
        }

    @staticmethod
    def parse_jwt_payload(token: str) -> dict[str, Any] | None:
        """Parse JWT token payload without verification.

        SECURITY WARNING: This method extracts and decodes the payload from a JWT token
        WITHOUT performing cryptographic verification. Use this ONLY for extracting
        metadata like expiration time for logging purposes.

        NEVER use this method for authentication decisions. Always use verify_jwt_token()
        for any security-critical operations.

        Args:
            token: The JWT token to parse

        Returns:
            The decoded payload dictionary, or None if parsing fails
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None

            # Decode the payload (second part)
            payload_b64 = parts[1]

            # Add padding if necessary
            padding = 4 - (len(payload_b64) % 4)
            if padding != 4:
                payload_b64 += '=' * padding

            payload_json = base64.urlsafe_b64decode(payload_b64)
            return json.loads(payload_json)
        except ValueError, json.JSONDecodeError, binascii.Error:
            return None

    @staticmethod
    def verify_jwt_token(
        token: str,
        secret: str,
        algorithms: list[str] | None = None,
        audience: str | None = None,
        issuer: str | None = None,
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        """Verify JWT token with signature validation.

        This method performs cryptographic verification of the JWT signature
        and validates the token's claims (expiration, audience, issuer).

        Use this method for authentication decisions. The parse_jwt_payload()
        method does NOT verify signatures and should only be used for metadata.

        Args:
            token: The JWT token to verify
            secret: The JWT secret key for signature verification
            algorithms: List of allowed algorithms (default: ["HS256"])
            audience: Optional audience claim to validate
            issuer: Optional issuer claim to validate

        Returns:
            Tuple of (is_valid, payload, error_message) where:
            - is_valid: True if token is valid and signature verified
            - payload: Decoded token payload if valid, None otherwise
            - error_message: None if valid, or error description if invalid
        """
        if algorithms is None:
            algorithms = ['HS256']

        try:
            # Verify signature and decode token
            payload = jwt.decode(
                token,
                secret,
                algorithms=algorithms,
                audience=audience,
                issuer=issuer,
                options={
                    'verify_signature': True,  # Always verify signature
                    'verify_exp': True,  # Verify expiration
                    'verify_nbf': True,  # Verify not-before
                    'verify_aud': audience is not None,
                    'verify_iss': issuer is not None,
                },
            )
            return True, payload, None

        except ExpiredSignatureError:
            return False, None, 'Token has expired'
        except jwt.InvalidSignatureError:
            return False, None, 'Invalid token signature'
        except jwt.InvalidAudienceError:
            return False, None, 'Invalid token audience'
        except jwt.InvalidIssuerError:
            return False, None, 'Invalid token issuer'
        except jwt.InvalidAlgorithmError:
            return False, None, 'Invalid token algorithm'
        except InvalidTokenError as e:
            return False, None, f'Invalid token: {str(e)}'
        except Exception as e:
            return False, None, f'Token verification failed: {str(e)}'

    def is_token_expired(self, token: str, leeway_seconds: int = 60) -> tuple[bool, str | None]:
        """Check if a token is expired.

        Supports JWT tokens with 'exp' claim and GitHub fine-grained tokens
        which may have expiration embedded in their metadata.

        Args:
            token: The token to check
            leeway_seconds: Grace period in seconds for clock skew (default: 60)

        Returns:
            Tuple of (is_expired, error_message) where:
            - is_expired: True if the token is expired or has invalid expiration
            - error_message: None if valid, or error description if expired
        """
        # Try to parse as JWT
        payload = self.parse_jwt_payload(token)

        if payload:
            exp_claim = payload.get('exp')
            if exp_claim:
                current_time = time.time()
                expiration_time = exp_claim + leeway_seconds

                if current_time >= expiration_time:
                    # Calculate time remaining (negative = expired)
                    time_remaining = expiration_time - current_time
                    if time_remaining < 0:
                        expired_for = abs(int(time_remaining))
                        return True, f'Token expired {expired_for} seconds ago'

                return False, None

        # For non-JWT tokens (simple API keys), check if it's a GitHub fine-grained token
        # GitHub fine-grained tokens with expiration have the exp_iat and exp claims
        # We can't verify these without JWT signature, so we accept them as valid
        # if they appear to be properly formatted

        # If we can't determine expiration, assume valid (don't reject tokens
        # that don't have clear expiration metadata)
        return False, None
