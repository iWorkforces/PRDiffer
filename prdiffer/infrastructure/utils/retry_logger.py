"""Logging utilities for retry handler."""

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
        error_msg = str(error)
        if len(error_msg) > 100:
            error_msg = error_msg[:97] + "..."
        message = "API error%s, retrying in %.2fs (attempt %d): %s" % (
            context_str,
            delay,
            attempt + 1,
            error_msg,
        )

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
    if not should_retry:
        error_msg = str(error)
        if len(error_msg) > 150:
            error_msg = error_msg[:147] + "..."
        message = f"Permanent failure (no retry configured): {error_msg}"
        log_at_level(logger, message, permanent_failure_log_level)
    elif is_last_attempt:
        message = f"All retry attempts exhausted: {str(error)[:100]}..."
        log_at_level(logger, message, "ERROR")


def log_at_level(logger: logging.Logger, message: str, level: str) -> None:
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
        logger.info(message)
