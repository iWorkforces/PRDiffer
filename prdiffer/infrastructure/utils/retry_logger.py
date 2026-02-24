"""Logging utilities for retry handler.

This module provides utilities for logging retry attempts,
rate limit information, and failures.
"""

import logging
from collections.abc import Callable

from prdiffer.infrastructure.utils.rate_limit_parser import (
    RateLimitInfo,
    is_rate_limit_remaining_below_threshold,
)


def log_retry_attempt(
    logger: logging.Logger,
    attempt: int,
    delay: float,
    error: Exception,
    retry_log_level: str,
    context: str | None = None,
    rate_limit_info: RateLimitInfo | None = None,
    is_secondary_rate_limit: bool = False,
    is_rate_limit_checker: Callable[[Exception], bool] = lambda e: False,
) -> None:
    """Log retry attempt information at configured level.

    Args:
        logger: Logger instance
        attempt: Current attempt number (0-based)
        delay: Delay before next retry in seconds
        error: Exception that caused the retry
        retry_log_level: Log level for retry attempts
        context: Optional operation context string
        rate_limit_info: Parsed rate limit information
        is_secondary_rate_limit: Whether this is a secondary rate limit error
        is_rate_limit_checker: Function to check if error is rate limit error
    """
    is_rate_limit = is_rate_limit_checker(error)
    context_str = f" [{context}]" if context else ""

    if is_rate_limit:
        label = "Secondary rate limit" if is_secondary_rate_limit else "Rate limit"
        message = "%s hit%s, retrying in %.2fs (attempt %d)" % (
            label,
            context_str,
            delay,
            attempt + 1,
        )
    else:
        # Truncate long error messages for cleaner logs
        error_msg = str(error)
        if len(error_msg) > 100:
            error_msg = error_msg[:97] + "..."
        message = "API error%s, retrying in %.2fs (attempt %d): %s" % (
            context_str,
            delay,
            attempt + 1,
            error_msg,
        )

    # Log at configured level
    log_at_level(logger, message, retry_log_level)

    if rate_limit_info:
        log_rate_limit_headers(
            logger,
            rate_limit_info,
            is_secondary_rate_limit,
            rate_limit_remaining_threshold=1,
        )


def log_rate_limit_headers(
    logger: logging.Logger,
    rate_limit_info: RateLimitInfo,
    is_secondary_rate_limit: bool,
    rate_limit_remaining_threshold: int = 1,
) -> None:
    """Log rate limit header information.

    Args:
        logger: Logger instance
        rate_limit_info: Parsed rate limit information
        is_secondary_rate_limit: Whether this is a secondary rate limit error
        rate_limit_remaining_threshold: Threshold for warning
    """
    level = "WARNING" if is_secondary_rate_limit else "INFO"
    message = "Rate limit headers: remaining=%s limit=%s reset=%s retry_after=%s" % (
        rate_limit_info.remaining,
        rate_limit_info.limit,
        rate_limit_info.reset_at,
        rate_limit_info.retry_after,
    )
    log_at_level(logger, message, level)

    if is_rate_limit_remaining_below_threshold(rate_limit_info, rate_limit_remaining_threshold):
        threshold_message = "Rate limit remaining below threshold: %d <= %d" % (
            rate_limit_info.remaining,
            rate_limit_remaining_threshold,
        )
        log_at_level(logger, threshold_message, "WARNING")


def log_permanent_failure(
    logger: logging.Logger,
    error: Exception,
    permanent_failure_log_level: str,
    should_retry: bool,
    is_last_attempt: bool,
) -> None:
    """Log permanent failure or final attempt information.

    Args:
        logger: Logger instance
        error: Exception that caused the failure
        permanent_failure_log_level: Log level for permanent failures
        should_retry: Whether this error type is configured for retry
        is_last_attempt: Whether this was the last retry attempt
    """
    if not should_retry:
        # Permanent failure due to error type
        error_msg = str(error)
        if len(error_msg) > 150:
            error_msg = error_msg[:147] + "..."
        message = f"Permanent failure (no retry configured): {error_msg}"
        log_at_level(logger, message, permanent_failure_log_level)
    elif is_last_attempt:
        # Final attempt failed
        message = f"All retry attempts exhausted: {str(error)[:100]}..."
        log_at_level(logger, message, "ERROR")


def log_at_level(logger: logging.Logger, message: str, level: str) -> None:
    """Log message at specified level.

    Args:
        logger: Logger instance
        message: Message to log
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level = level.upper()
    if level == "DEBUG":
        logger.debug(message)
    elif level == "INFO":
        logger.info(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "CRITICAL":
        logger.critical(message)
    else:
        # Fallback to INFO for unknown levels
        logger.info(message)
