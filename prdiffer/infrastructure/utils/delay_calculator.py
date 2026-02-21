"""Retry delay calculation utilities.

This module provides utilities for calculating retry delays with
various strategies including exponential backoff, jitter,
and rate limit awareness.
"""

import random
from typing import TYPE_CHECKING

from prdiffer.infrastructure.utils.rate_limit_parser import RateLimitInfo
from prdiffer.infrastructure.utils.error_classifier import is_rate_limit_error

if TYPE_CHECKING:
    from prdiffer.infrastructure.utils.api_health_tracker import APIHealthTracker


def calculate_basic_backoff(attempt: int, base_delay: float, is_rate_limit: bool = False) -> float:
    """Calculate basic backoff delay with exponential growth and jitter.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        is_rate_limit: Whether this is a rate limit error (doubles delay)

    Returns:
        float: Delay in seconds before next retry
    """
    exponential_delay = base_delay * (2**attempt)
    jitter = random.uniform(0, exponential_delay * 0.1)  # 10% jitter
    delay = exponential_delay + jitter

    # Rate limit errors get longer delays
    if is_rate_limit:
        return delay * 2

    return float(delay)


def calculate_adaptive_delay(
    attempt: int,
    base_delay: float,
    backoff_multiplier: float,
    error: Exception | None = None,
    health_tracker: 'APIHealthTracker | None' = None,
    max_delay: float = 30.0,
) -> float:
    """Calculate adaptive retry delay based on API health and error type.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay for this context
        backoff_multiplier: Backoff multiplier for this context
        error: Exception that caused the retry (optional)
        health_tracker: APIHealthTracker instance for adaptive delays (optional)
        max_delay: Maximum allowed delay in seconds

    Returns:
        float: Adaptive delay in seconds
    """
    # Basic exponential backoff
    exponential_delay = base_delay * (backoff_multiplier**attempt)

    # Add jitter
    jitter = random.uniform(0, exponential_delay * 0.1)
    delay_with_jitter = exponential_delay + jitter

    # Adaptive delay based on API health if tracker available
    if health_tracker:
        adaptive_delay = health_tracker.get_recommended_delay(delay_with_jitter, max_delay)
        return float(adaptive_delay)

    # Rate limit errors get longer delays
    if error and is_rate_limit_error(error):
        return min(delay_with_jitter * 2, max_delay)

    return delay_with_jitter


def calculate_secondary_rate_limit_backoff(attempt: int, base_backoff: float = 60.0) -> float:
    """Calculate backoff for secondary rate limit errors.

    Args:
        attempt: Current attempt number (0-based)
        base_backoff: Base delay in seconds for secondary rate limits

    Returns:
        float: Delay in seconds
    """
    base_delay = base_backoff * (2**attempt)
    jitter = random.uniform(0, base_delay * 0.1)
    return float(base_delay + jitter)


def calculate_retry_delay(
    attempt: int,
    error: Exception,
    base_delay: float,
    backoff_multiplier: float,
    rate_limit_info: RateLimitInfo | None = None,
    is_secondary_rate_limit: bool = False,
    use_adaptive: bool = False,
    secondary_backoff: float = 60.0,
    reset_buffer: float = 1.0,
    health_tracker: 'APIHealthTracker | None' = None,
    max_adaptive_delay: float = 30.0,
) -> float:
    """Calculate retry delay based on error type and configuration.

    Args:
        attempt: Current attempt number (0-based)
        error: Exception that caused the retry
        base_delay: Base delay for this context
        backoff_multiplier: Backoff multiplier for this context
        rate_limit_info: Parsed rate limit information
        is_secondary_rate_limit: Whether this is a secondary rate limit error
        use_adaptive: Whether to use adaptive retry delays
        secondary_backoff: Base delay for secondary rate limits
        reset_buffer: Seconds to add to reset-based delay
        health_tracker: APIHealthTracker instance for adaptive delays
        max_adaptive_delay: Maximum adaptive delay in seconds

    Returns:
        float: Delay in seconds
    """
    # Check for rate limit header delays first
    header_delay = None
    if rate_limit_info:
        if rate_limit_info.retry_after is not None:
            header_delay = rate_limit_info.retry_after
        elif rate_limit_info.reset_at is not None:
            import time

            delay = rate_limit_info.reset_at - time.time() + reset_buffer
            header_delay = max(0.0, delay)

    # Secondary rate limit errors get special backoff
    if is_secondary_rate_limit:
        secondary_delay = calculate_secondary_rate_limit_backoff(attempt, secondary_backoff)
        if header_delay is not None:
            return max(secondary_delay, header_delay)
        return secondary_delay

    # Use header delay if available
    if header_delay is not None:
        return header_delay

    # Adaptive delay if enabled
    if use_adaptive:
        return calculate_adaptive_delay(
            attempt,
            base_delay,
            backoff_multiplier,
            error=error,
            health_tracker=health_tracker,
            max_delay=max_adaptive_delay,
        )

    # Basic backoff with rate limit awareness
    return calculate_basic_backoff(attempt, base_delay, is_rate_limit_error(error))
