from abc import ABC, abstractmethod
from enum import StrEnum


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggerServiceInterface(ABC):
    """Logging service contract for different backends."""

    @abstractmethod
    def debug(self, message: str, **kwargs: object) -> None: ...

    @abstractmethod
    def info(self, message: str, **kwargs: object) -> None: ...

    @abstractmethod
    def warning(self, message: str, **kwargs: object) -> None: ...

    @abstractmethod
    def error(self, message: str, **kwargs: object) -> None: ...

    @abstractmethod
    def critical(self, message: str, **kwargs: object) -> None: ...

    @abstractmethod
    def should_log(self, level: LogLevel) -> bool: ...
