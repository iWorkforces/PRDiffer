"""Domain service interfaces for the PRDiffer application."""

from .cache import CacheServiceInterface
from .diff import DiffServiceInterface
from .logger import LoggerServiceInterface, LogLevel
from .pattern_matching import PatternMatchingServiceInterface
from .pr_diff_service import PRDiffServiceInterface
from .repository_cache import RepositoryCacheServiceInterface
from .retry import RetryServiceInterface
from .settings import SettingsServiceInterface
from .github_api import GitHubAPIServiceInterface

__all__ = [
    "CacheServiceInterface",
    "DiffServiceInterface",
    "LoggerServiceInterface",
    "LogLevel",
    "PatternMatchingServiceInterface",
    "PRDiffServiceInterface",
    "RepositoryCacheServiceInterface",
    "RetryServiceInterface",
    "SettingsServiceInterface",
    "GitHubAPIServiceInterface",
]
