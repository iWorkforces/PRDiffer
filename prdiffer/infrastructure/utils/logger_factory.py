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
import threading


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


class LazyLoggerMixin:
    """Mixin class providing lazy logger initialization with thread safety.

    This mixin implements the double-checked locking pattern for lazy logger
    initialization. It's used to avoid circular import issues when creating
    loggers in module initialization.

    The pattern used is:
    1. Logger can be None initially (passed to __init__)
    2. On first access via _get_logger(), create logger using get_logger()
    3. Use double-checked locking to ensure thread safety

    Classes using this mixin should:
    - Call self._init_lazy_logger(logger, logger_name) in __init__()
    - Use self._get_logger() instead of self._logger directly

    Example:
        class MyClass(LazyLoggerMixin):
            def __init__(self, logger=None):
                self._init_lazy_logger(logger, __name__)

            def do_work(self):
                logger = self._get_logger()
                logger.info("Doing work")
    """

    def _init_lazy_logger(self, logger: logging.Logger | None, logger_name: str) -> None:
        """Initialize lazy logger state.

        This should be called in __init__() of classes using this mixin.

        Args:
            logger: Optional logger instance. If None, will be lazily created.
            logger_name: Name for the logger (typically __name__)
        """
        self._logger: logging.Logger | None = logger
        self._logger_name = logger_name
        self._logger_fetched = logger is not None
        self._logger_lock = threading.Lock()

    def _get_logger(self) -> logging.Logger:
        """Get logger instance, lazily loading if needed to avoid circular imports.

        Uses double-checked locking pattern for thread safety.

        Returns:
            logging.Logger: Logger instance
        """
        if not self._logger_fetched:
            with self._logger_lock:
                # Double-check pattern to avoid race conditions
                if not self._logger_fetched:
                    self._logger = get_logger(self._logger_name)
                    self._logger_fetched = True
        return self._logger  # type: ignore[return-value]


def get_null_logger(name: str | None = None) -> logging.Logger:
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
