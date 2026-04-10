"""JWT token handling for authentication.

Extracted from authentication.py for maintainability.
Contains JWT token parsing, verification, and expiration checking.
"""

from __future__ import annotations

import base64
import binascii
import json
import time
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError


class JWTHandlerMixin:
    """Mixin providing JWT token handling capabilities.

    Provides static methods for JWT parsing and verification,
    plus instance methods for token expiration checking.
    """

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
            parts = token.split(".")
            if len(parts) != 3:
                return None

            payload_b64 = parts[1]

            padding = 4 - (len(payload_b64) % 4)
            if padding != 4:
                payload_b64 += "=" * padding

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
            algorithms = ["HS256"]

        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=algorithms,
                audience=audience,
                issuer=issuer,
                options={
                    "verify_signature": True,  # Always verify signature
                    "verify_exp": True,  # Verify expiration
                    "verify_nbf": True,  # Verify not-before
                    "verify_aud": audience is not None,
                    "verify_iss": issuer is not None,
                },
            )
            return True, payload, None

        except ExpiredSignatureError:
            return False, None, "Token has expired"
        except jwt.InvalidSignatureError:
            return False, None, "Invalid token signature"
        except jwt.InvalidAudienceError:
            return False, None, "Invalid token audience"
        except jwt.InvalidIssuerError:
            return False, None, "Invalid token issuer"
        except jwt.InvalidAlgorithmError:
            return False, None, "Invalid token algorithm"
        except InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            return False, None, f"Token verification failed: {str(e)}"

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
        payload = self.parse_jwt_payload(token)

        if payload:
            exp_claim = payload.get("exp")
            if exp_claim:
                current_time = time.time()
                expiration_time = exp_claim + leeway_seconds

                if current_time >= expiration_time:
                    time_remaining = expiration_time - current_time
                    if time_remaining < 0:
                        expired_for = abs(int(time_remaining))
                        return True, f"Token expired {expired_for} seconds ago"

                return False, None

        # For non-JWT tokens (simple API keys), check if it's a GitHub fine-grained token
        # GitHub fine-grained tokens with expiration have the exp_iat and exp claims
        # We can't verify these without JWT signature, so we accept them as valid
        # if they appear to be properly formatted

        # If we can't determine expiration, assume valid (don't reject tokens
        # that don't have clear expiration metadata)
        return False, None
