"""Retry handler constants and enums."""

from enum import StrEnum

try:
    from github import GithubException as PyGithubException
except Exception:
    PyGithubException: type[BaseException] | None = None


RETRY_EXCEPTIONS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionError,
    OSError,
    IOError,
    EOFError,
)

if PyGithubException is not None:
    RETRY_EXCEPTIONS = RETRY_EXCEPTIONS + (PyGithubException,)


class OperationContext(StrEnum):
    """Context types for different operations."""

    REPOSITORY_ACCESS = 'repository_access'
    FILE_CONTENT = 'file_content'
    PULL_REQUEST = 'pull_request'
    BATCH_OPERATION = 'batch_operation'
