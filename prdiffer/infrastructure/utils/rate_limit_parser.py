"""Rate limit header parsing utilities.

This module provides utilities for parsing GitHub rate limit headers
from HTTP responses and exceptions.
"""

import time
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitInfo:
    """Parsed GitHub rate limit headers.

    Attributes:
        remaining: Remaining API requests in current quota
        limit: Total API requests allowed in quota window
        reset_at: Unix timestamp when quota resets
        retry_after: Seconds to wait before retrying (from Retry-After header)
    """

    remaining: Optional[int]
    limit: Optional[int]
    reset_at: Optional[int]
    retry_after: Optional[float]


def get_error_headers(error: Exception) -> Optional[dict[str, str]]:
    """Extract headers from a GitHub exception if available.

    Args:
        error: Exception to extract headers from

    Returns:
        Optional[dict[str, str]]: Headers dictionary or None if not available
    """
    headers = getattr(error, "headers", None)
    if headers is None:
        response = getattr(error, "response", None)
        headers = getattr(response, "headers", None) if response is not None else None

    if not headers:
        return None

    try:
        return {str(key): str(value) for key, value in headers.items()}
    except Exception:
        return None


def parse_int_header(headers: dict[str, str], name: str) -> Optional[int]:
    """Parse an integer header value from headers dictionary.

    Args:
        headers: Headers dictionary
        name: Header name (case-insensitive)

    Returns:
        Optional[int]: Parsed integer value or None if not found/invalid
    """
    for key, value in headers.items():
        if key.lower() == name.lower():
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def parse_retry_after(headers: dict[str, str]) -> Optional[float]:
    """Parse Retry-After header value from headers dictionary.

    The Retry-After header can be specified as:
    - Seconds (e.g., "60")
    - HTTP date (e.g., "Wed, 21 Oct 2015 07:28:00 GMT")

    Args:
        headers: Headers dictionary

    Returns:
        Optional[float]: Seconds to wait or None if not found/invalid
    """
    retry_after_value = None
    for key, value in headers.items():
        if key.lower() == "retry-after":
            retry_after_value = value
            break

    if retry_after_value is None:
        return None

    try:
        return max(0.0, float(retry_after_value))
    except (TypeError, ValueError):
        try:
            parsed = parsedate_to_datetime(str(retry_after_value))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            delay = parsed.timestamp() - time.time()
            return max(0.0, delay)
        except (TypeError, ValueError, OverflowError):
            return None


def extract_rate_limit_info(error: Exception) -> Optional[RateLimitInfo]:
    """Extract rate limit information from an exception.

    Parses GitHub rate limit headers from the exception if available.

    Args:
        error: Exception that may contain rate limit headers

    Returns:
        Optional[RateLimitInfo]: Parsed rate limit info or None if not available
    """
    headers = get_error_headers(error)
    if not headers:
        return None

    remaining = parse_int_header(headers, "X-RateLimit-Remaining")
    limit = parse_int_header(headers, "X-RateLimit-Limit")
    reset_at = parse_int_header(headers, "X-RateLimit-Reset")
    retry_after = parse_retry_after(headers)

    if remaining is None and limit is None and reset_at is None and retry_after is None:
        return None

    return RateLimitInfo(
        remaining=remaining,
        limit=limit,
        reset_at=reset_at,
        retry_after=retry_after,
    )


def calculate_rate_limit_delay(
    rate_limit_info: Optional[RateLimitInfo],
    reset_buffer: float = 1.0,
) -> Optional[float]:
    """Calculate delay needed based on rate limit information.

    Args:
        rate_limit_info: Parsed rate limit information
        reset_buffer: Seconds to add to reset-based delay as safety buffer

    Returns:
        Optional[float]: Delay in seconds or None if no delay needed
    """
    if rate_limit_info is None:
        return None

    if rate_limit_info.retry_after is not None:
        return rate_limit_info.retry_after

    if rate_limit_info.reset_at is not None:
        delay = rate_limit_info.reset_at - time.time() + reset_buffer
        return max(0.0, delay)

    return None


def is_rate_limit_remaining_below_threshold(
    rate_limit_info: Optional[RateLimitInfo],
    threshold: int = 1,
) -> bool:
    """Check if remaining rate limit is below threshold.

    Args:
        rate_limit_info: Parsed rate limit information
        threshold: Minimum remaining requests threshold

    Returns:
        bool: True if remaining is below threshold or info unavailable
    """
    if rate_limit_info is None:
        return False

    if rate_limit_info.remaining is None:
        return False

    return rate_limit_info.remaining <= threshold
