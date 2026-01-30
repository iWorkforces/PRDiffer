"""Logger factory utility for consistent logging across infrastructure layer.

This module provides a simple, thread-safe utility for obtaining logger instances
using Python's standard logging module. The logging.Logger class is thread-safe
by design, so no additional locking is required.

Example Usage:
    from prdiffer.infrastructure.utils.logger_factory import get_logger

    logger = get_logger(__name__)
    logger.info("Processing started")
    logger.debug("Detailed diagnostic information")

Thread Safety:
    Python's logging.Logger is thread-safe by design. Multiple threads can
    safely call logging methods on the same logger instance without external
    synchronization.
"""

import logging
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    This is a simple wrapper around logging.getLogger() that provides
    consistent logger instantiation across the infrastructure layer.

    Args:
        name: The name for the logger, typically __name__ of the calling module.

    Returns:
        logging.Logger: A logger instance with the specified name.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)


def get_null_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a null logger that suppresses all log output.

    This is useful for testing or when you need to suppress logging
    entirely. The null logger has its level set to CRITICAL and
    propagates to None, preventing any log output.

    Args:
        name: Optional name for the logger. If not provided, a default
            name "null_logger" is used.

    Returns:
        logging.Logger: A logger instance that suppresses all output.

    Example:
        >>> logger = get_null_logger(__name__)
        >>> logger.debug("This will not be logged")
        >>> logger.info("This will not be logged either")
    """
    logger = logging.getLogger(name or "null_logger")
    logger.setLevel(logging.CRITICAL + 1)  # Set above all standard levels
    logger.propagate = False  # Don't propagate to root logger
    return logger
