import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from ccpragents.infrastructure.settings import get_settings_service
from ccpragents.domain.services import LoggerServiceInterface, LogLevel


class ConsoleLogger(LoggerServiceInterface):
    """Console-based logging service implementation.

    This logger outputs messages to the console (stdout/stderr) with
    colored formatting and follows the application's logging configuration.
    """

    # ANSI color codes for console output
    COLORS = {
        LogLevel.DEBUG: "\033[36m",     # Cyan
        LogLevel.INFO: "\033[32m",      # Green
        LogLevel.WARNING: "\033[33m",   # Yellow
        LogLevel.ERROR: "\033[31m",     # Red
        LogLevel.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self):
        """Initialize the console logger with settings from configuration."""
        self.settings_service = get_settings_service()
        self._configure_logger()

    def _configure_logger(self) -> None:
        """Configure the logger based on application settings."""
        app_settings = self.settings_service.get_app_settings()
        self.enabled = app_settings.get('logging_enabled', True)

        # Map string log level to LogLevel enum
        log_level_str = app_settings.get('log_level', 'INFO').upper()
        self.log_level = getattr(LogLevel, log_level_str, LogLevel.INFO)

        # Set up Python logging if needed
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stdout
        )

    def should_log(self, level: LogLevel) -> bool:
        """Check if a message of the given level should be logged.

        Args:
            level: The log level to check

        Returns:
            bool: True if the level should be logged, False otherwise
        """
        if not self.enabled:
            return False

        # Convert both levels to numerical values for comparison
        level_values = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50,
        }

        current_level_value = level_values.get(self.log_level, 20)
        message_level_value = level_values.get(level, 20)

        return message_level_value >= current_level_value

    def debug(self, message: str, **kwargs) -> None:
        """Log a debug level message.

        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        if self.should_log(LogLevel.DEBUG):
            self._log(LogLevel.DEBUG, message, kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log an info level message.

        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        if self.should_log(LogLevel.INFO):
            self._log(LogLevel.INFO, message, kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log a warning level message.

        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        if self.should_log(LogLevel.WARNING):
            self._log(LogLevel.WARNING, message, kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log an error level message.

        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        if self.should_log(LogLevel.ERROR):
            self._log(LogLevel.ERROR, message, kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log a critical level message.

        Args:
            message: The message to log
            **kwargs: Additional context data
        """
        if self.should_log(LogLevel.CRITICAL):
            self._log(LogLevel.CRITICAL, message, kwargs)

    def _log(self, level: LogLevel, message: str, context: Dict[str, Any]) -> None:
        """Internal method to format and output log messages.

        Args:
            level: The log level
            message: The message to log
            context: Additional context data
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color = self.COLORS.get(level, self.RESET)

        # Format the message with context
        if context:
            context_str = " ".join([f"{k}={v}" for k, v in context.items()])
            formatted_message = f"{message} [{context_str}]"
        else:
            formatted_message = message

        # Output to console with color and timestamp
        log_line = f"{color}{timestamp} - {level.value} - {formatted_message}{self.RESET}"

        # Use stderr for errors and critical messages
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            print(log_line, file=sys.stderr)
        else:
            print(log_line)


# Global logger instance
_logger_instance: Optional[ConsoleLogger] = None


def get_logger() -> ConsoleLogger:
    """Get or create the global logger instance.

    Returns:
        ConsoleLogger: The global logger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ConsoleLogger()
    return _logger_instance
