import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any
from prdiffer.infrastructure.settings import get_settings_service
from prdiffer.domain.services import LoggerServiceInterface, LogLevel


class ConsoleLogger(LoggerServiceInterface):
    """Console-based logging service implementation.

    This logger outputs messages to the console (stdout/stderr) with
    colored formatting and follows the application's logging configuration.
    Supports both text and JSON output formats.

    Example Usage:
        # Text format (default)
        logger.info("Processing started", request_id="abc123")
        # Output: 2024-01-20T10:30:00Z - INFO - Processing started [request_id=abc123]

        # JSON format (set logging.format = "json" in settings.toml)
        # Output: {"timestamp": "2024-01-20T10:30:00Z", "level": "INFO",
        #          "message": "Processing started", "context": {"request_id": "abc123"}}

    Log Levels:
        - DEBUG: Detailed diagnostic information (Cyan)
        - INFO: General application flow (Green)
        - WARNING: Potential issues (Yellow)
        - ERROR: Error conditions (Red)
        - CRITICAL: Severe errors (Magenta)
    """

    # ANSI color codes for console output
    COLORS = {
        LogLevel.DEBUG: "\033[36m",  # Cyan
        LogLevel.INFO: "\033[32m",  # Green
        LogLevel.WARNING: "\033[33m",  # Yellow
        LogLevel.ERROR: "\033[31m",  # Red
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
        self.enabled = app_settings.get("logging_enabled", True)

        # Map string log level to LogLevel enum
        log_level_str = app_settings.get("log_level", "INFO").upper()
        self.log_level = getattr(LogLevel, log_level_str, LogLevel.INFO)

        transport = os.getenv("MCP_TRANSPORT") or self.settings_service.get(
            "mcp.transport", "stdio"
        )
        self._force_stderr = transport == "stdio"

        # Get log format from settings (simple, json, structured)
        self._log_format = self.settings_service.get("logging.format", "simple")
        self._json_pretty = self.settings_service.get("logging.json_pretty", False)

        # Set up Python logging if needed
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stderr if self._force_stderr else sys.stdout,
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

    def is_enabled_for(self, level: str) -> bool:
        """Check if logging is enabled for the given level.

        Args:
            level: The log level to check (e.g., "DEBUG", "INFO", "WARNING")

        Returns:
            bool: True if logging is enabled for the level
        """
        log_level = getattr(LogLevel, level.upper(), None)
        if log_level is None:
            return False
        return self.should_log(log_level)

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

    def _log(self, level: LogLevel, message: str, context: dict[str, Any]) -> None:
        """Internal method to format and output log messages.

        Args:
            level: The log level
            message: The message to log
            context: Additional context data
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        color = self.COLORS.get(level, self.RESET)

        # Output to console with color and timestamp
        if self._log_format == "json":
            self._log_json(level, message, context, timestamp)
        else:
            self._log_text(level, message, context, timestamp, color)

    def _log_text(
        self,
        level: LogLevel,
        message: str,
        context: dict[str, Any],
        timestamp: str,
        color: str,
    ) -> None:
        """Format and output log messages in text format.

        Args:
            level: The log level
            message: The message to log
            context: Additional context data
            timestamp: Formatted timestamp string
            color: ANSI color code for the level
        """
        # Format the message with context
        if context:
            context_str = " ".join([f"{k}={v}" for k, v in context.items()])
            formatted_message = f"{message} [{context_str}]"
        else:
            formatted_message = message

        log_line = (
            f"{color}{timestamp} - {level.value} - {formatted_message}{self.RESET}"
        )

        # Use stderr for stdio mode or for error/critical messages
        stream = sys.stderr if self._force_stderr else sys.stdout
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            stream = sys.stderr
        print(log_line, file=stream)

    def _log_json(
        self, level: LogLevel, message: str, context: dict[str, Any], timestamp: str
    ) -> None:
        """Format and output log messages in JSON format.

        Args:
            level: The log level
            message: The message to log
            context: Additional context data
            timestamp: ISO format timestamp
        """
        log_record = {
            "timestamp": timestamp,
            "level": level.value,
            "message": message,
            "context": context,
        }

        # Use stderr for stdio mode or for error/critical messages
        stream = sys.stderr if self._force_stderr else sys.stdout
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            stream = sys.stderr

        if self._json_pretty:
            print(json.dumps(log_record, indent=2), file=stream)
        else:
            print(json.dumps(log_record), file=stream)


# Global logger instance
_logger_instance: ConsoleLogger | None = None


def get_logger() -> ConsoleLogger:
    """Get or create the global logger instance.

    Returns:
        ConsoleLogger: The global logger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ConsoleLogger()
    return _logger_instance
