"""Logging infrastructure for PRDiffer.

This package provides logging utilities including structured console logging
and exception sanitization for secure log output.
"""

from .console_logger import ConsoleLogger, get_logger
from .exception_utils import (
    ExceptionSanitizer,
    sanitize_exception_message,
    sanitize_traceback,
    sanitize_exception_for_logging,
    redact_auth_header,
)

__all__ = [
    "ConsoleLogger",
    "get_logger",
    "ExceptionSanitizer",
    "sanitize_exception_message",
    "sanitize_traceback",
    "sanitize_exception_for_logging",
    "redact_auth_header",
]
