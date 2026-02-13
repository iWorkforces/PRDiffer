"""GitHub API client constants and models."""

from github import GithubException

GITHUB_API_EXCEPTIONS: tuple[type[BaseException], ...] = (
    GithubException,
    TimeoutError,
    ConnectionError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)

DEFAULT_FILE_CONTENT_CACHE_MAX_SIZE = 1000
DEFAULT_FILE_CONTENT_CACHE_TTL = 600
