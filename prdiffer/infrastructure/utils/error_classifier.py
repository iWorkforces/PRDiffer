"""Error classification utilities for retry logic.

This module provides utilities for classifying and analyzing errors
to determine retry behavior and categorization.
"""

from dataclasses import dataclass


# Pre-defined error code sets for efficient lookups
PERMANENT_ERROR_CODES = {'404', '401', '403'}
SERVER_ERROR_CODES = {'500', '501', '502', '503', '504'}
TRANSIENT_ERROR_PATTERNS = {'timeout', 'connection', 'network', '503', '502', '504'}
SECONDARY_RATE_LIMIT_PATTERNS = {
    'secondary rate limit',
    'abuse detection',
    'abuse detection mechanism',
    'api abuse',
    'temporarily blocked',
}


def is_permanent_error(error_code: str) -> bool:
    """Check if an error code represents a permanent error.

    Args:
        error_code: HTTP status code string (e.g., "404", "403")

    Returns:
        bool: True if this is a permanent error
    """
    return error_code in PERMANENT_ERROR_CODES


def is_server_error(error_code: str) -> bool:
    """Check if an error code represents a server error.

    Args:
        error_code: HTTP status code string (e.g., "500", "503")

    Returns:
        bool: True if this is a server error
    """
    return error_code in SERVER_ERROR_CODES


def is_transient_error(error_message: str) -> bool:
    """Check if an error message indicates a transient error.

    Args:
        error_message: Error message string

    Returns:
        bool: True if this is a transient error
    """
    error_message_lower = error_message.lower()
    return any(pattern in error_message_lower for pattern in TRANSIENT_ERROR_PATTERNS)


def is_secondary_rate_limit_error(error: Exception) -> bool:
    """Detect secondary rate limit (abuse detection) errors.

    Args:
        error: Exception to check

    Returns:
        bool: True if this is a secondary rate limit error
    """
    message = get_error_message(error)
    return any(pattern in message for pattern in SECONDARY_RATE_LIMIT_PATTERNS)


def get_error_message(error: Exception) -> str:
    """Get combined error message for classification.

    Args:
        error: Exception to extract message from

    Returns:
        str: Combined error message (base message + data message if available)
    """
    base_message = str(error)
    data_message = ''
    data = getattr(error, 'data', None)
    if isinstance(data, dict):
        data_message = str(data.get('message', ''))
    elif isinstance(data, str):
        data_message = data
    return f'{base_message} {data_message}'.strip().lower()


def categorize_error(error: Exception) -> str:
    """Categorize error for health tracking.

    Args:
        error: Exception to categorize

    Returns:
        str: Error category (not_found, authentication, rate_limit, server_error, timeout, network, unknown)
    """
    error_str = str(error).lower()

    if '404' in error_str:
        return 'not_found'
    elif '403' in error_str or '401' in error_str:
        return 'authentication'
    elif '429' in error_str or 'rate limit' in error_str:
        return 'rate_limit'
    elif any(f'{code}' in error_str for code in [500, 502, 503, 504]):
        return 'server_error'
    elif 'timeout' in error_str:
        return 'timeout'
    elif 'connection' in error_str or 'network' in error_str:
        return 'network'
    else:
        return 'unknown'


def should_retry_by_error_code(
    error_message: str,
    retry_on_404: bool,
    retry_on_403: bool,
    retry_on_500: bool,
) -> bool:
    """Determine if an error should be retried based on HTTP status codes.

    Args:
        error_message: Error message string
        retry_on_404: Whether to retry 404 errors
        retry_on_403: Whether to retry 403 errors
        retry_on_500: Whether to retry 5xx server errors

    Returns:
        bool: True if this error should be retried based on code
    """
    if '404' in error_message and not retry_on_404:
        return False
    if '403' in error_message and not retry_on_403:
        return False
    if any(code in error_message for code in SERVER_ERROR_CODES) and not retry_on_500:
        return False
    return True


def is_rate_limit_error(error: Exception) -> bool:
    """Check if an exception indicates a rate limit error.

    Args:
        error: Exception to check

    Returns:
        bool: True if this is a rate limit error
    """
    error_str = str(error).lower()
    if is_secondary_rate_limit_error(error):
        return True

    if 'rate limit' in error_str or '429' in str(error):
        return True

    return False


@dataclass
class RetryDecision:
    """Result of error classification for retry decision."""

    should_retry: bool
    reason: str
    is_rate_limit: bool
    is_permanent: bool


def classify_error_for_retry(
    error: Exception,
    retry_on_404: bool = False,
    retry_on_403: bool = True,
    retry_on_500: bool = True,
) -> RetryDecision:
    """Classify an error and determine if it should be retried.

    Args:
        error: Exception to classify
        retry_on_404: Whether to retry 404 errors
        retry_on_403: Whether to retry 403 errors
        retry_on_500: Whether to retry 5xx server errors

    Returns:
        RetryDecision: Classification result with retry decision
    """
    error_message = str(error).lower()

    # Check for permanent errors
    if '404' in error_message and not retry_on_404:
        return RetryDecision(
            should_retry=False,
            reason='404 Not Found (not configured for retry)',
            is_rate_limit=False,
            is_permanent=True,
        )

    if '403' in error_message and not retry_on_403:
        return RetryDecision(
            should_retry=False,
            reason='403 Forbidden (not configured for retry)',
            is_rate_limit=False,
            is_permanent=True,
        )

    if any(code in error_message for code in SERVER_ERROR_CODES) and not retry_on_500:
        return RetryDecision(
            should_retry=False,
            reason='Server error (not configured for retry)',
            is_rate_limit=False,
            is_permanent=True,
        )

    # Check for rate limit errors
    is_rate_limit = is_rate_limit_error(error)

    # Check for transient errors
    is_transient = is_transient_error(error_message)

    if is_transient or is_rate_limit:
        return RetryDecision(
            should_retry=True,
            reason='Transient error detected' if is_transient else 'Rate limit detected',
            is_rate_limit=is_rate_limit,
            is_permanent=False,
        )

    return RetryDecision(
        should_retry=False,
        reason='Error not classified as retryable',
        is_rate_limit=False,
        is_permanent=True,
    )
