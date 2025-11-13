"""Domain service interfaces for the CCPRAgents application."""

from .cache import CacheServiceInterface
from .diff import DiffServiceInterface
from .file_processing import FileProcessingServiceInterface
from .logger import LoggerServiceInterface, LogLevel
from .pattern_matching import PatternMatchingServiceInterface
from .pr_diff import PRDiffServiceInterface
from .repository_cache import RepositoryCacheServiceInterface
from .retry import RetryServiceInterface
from .settings import SettingsServiceInterface
from .github_api import GitHubAPIServiceInterface

__all__ = [
    "CacheServiceInterface",
    "DiffServiceInterface",
    "FileProcessingServiceInterface",
    "LoggerServiceInterface",
    "LogLevel",
    "PatternMatchingServiceInterface",
    "PRDiffServiceInterface",
    "RepositoryCacheServiceInterface",
    "RetryServiceInterface",
    "SettingsServiceInterface",
    "GitHubAPIServiceInterface",
]
