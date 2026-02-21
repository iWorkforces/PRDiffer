from abc import ABC, abstractmethod
from enum import StrEnum


class LogLevel(StrEnum):
    """Log levels for the logging service."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggerServiceInterface(ABC):
    """Abstract base class for logging services.

    This interface defines the contract for logging services that can be
    implemented with different logging backends while following the
    application's logging configuration.
    """

    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log a debug level message.

        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        pass

    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log an info level message.

        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log a warning level message.

        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        pass

    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log an error level message.

        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        pass

    @abstractmethod
    def critical(self, message: str, **kwargs) -> None:
        """Log a critical level message.

        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        pass

    @abstractmethod
    def should_log(self, level: LogLevel) -> bool:
        """Check if a message of the given level should be logged.

        Args:
            level: The log level to check

        Returns:
            bool: True if the level should be logged, False otherwise
        """
        pass
