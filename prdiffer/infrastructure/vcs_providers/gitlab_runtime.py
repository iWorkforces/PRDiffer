"""Bounded GitLab SDK execution: capacity, deadlines, status-aware mapping.

Process-shared CapacityLimiter, operation-scoped python-gitlab clients,
monotonic remaining-budget calculation, and typed exception translation.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar

import anyio
import gitlab
import requests

from prdiffer.domain.config.gitlab_config import GitLabConfig
from prdiffer.domain.error_codes import (
    E2006_GITLAB_AUTH_FAILED,
    E2007_GITLAB_INSUFFICIENT_PERMISSIONS,
    E3006_GITLAB_RATE_LIMITED,
    E4001_REPO_NOT_FOUND,
    E4002_PR_NOT_FOUND,
    E4003_FILE_NOT_FOUND,
    E5004_TIMEOUT_ERROR,
    E5019_CONNECTION_ERROR,
    E5021_GITLAB_API_ERROR,
)
from prdiffer.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    GitLabAPIError,
    RateLimitError,
    TimeoutError as DomainTimeoutError,
)

T = TypeVar("T")

GITLAB_COM_URL = "https://gitlab.com"


class GitLabNotFoundKind(StrEnum):
    """Context for mapping a verified 404 to the correct not-found code."""

    PROJECT = "project"
    MERGE_REQUEST = "merge_request"
    FILE = "file"


@dataclass(frozen=True, slots=True)
class GitLabNotFoundContext:
    """Operation-supplied 404 interpretation (project / MR / file)."""

    kind: GitLabNotFoundKind


def _safe_status(exc: BaseException) -> int | None:
    code = getattr(exc, "response_code", None)
    return code if isinstance(code, int) else None


def _parse_retry_after(exc: BaseException, remaining: float) -> int | None:
    """Parse Retry-After from SDK exception headers when present; bound by remaining."""
    headers = getattr(exc, "response_headers", None) or {}
    raw = None
    if isinstance(headers, dict):
        raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is None:
        # Some GitlabHttpError instances only expose response_body; skip secrets.
        return None
    try:
        value = int(raw)
    except TypeError, ValueError:
        return None
    if value < 0:
        return None
    bound = max(0, int(math.floor(remaining)))
    return min(value, bound) if bound > 0 else 0


def map_gitlab_exception(
    exc: BaseException,
    *,
    not_found: GitLabNotFoundContext | None = None,
    remaining_budget: float = 0.0,
) -> BaseException:
    """Translate python-gitlab / requests failures to domain exceptions.

    Never copies response_body, tokens, or credential-bearing URLs into details.
    """
    if isinstance(exc, (DomainTimeoutError, AuthenticationError, AuthorizationError, RateLimitError, GitLabAPIError)):
        return exc

    status = _safe_status(exc)

    if isinstance(exc, requests.Timeout) or (isinstance(exc, requests.RequestException) and "timeout" in type(exc).__name__.lower()):
        return DomainTimeoutError(
            "GitLab request timed out",
            error_code=E5004_TIMEOUT_ERROR,
            details={"status_code": status} if status is not None else None,
        )

    if isinstance(exc, (requests.ConnectionError, gitlab.GitlabConnectionError)):
        return GitLabAPIError(
            "Connection to GitLab failed",
            status_code=status,
            error_code=E5019_CONNECTION_ERROR,
            details={},
        )

    if status == 401 or isinstance(exc, gitlab.GitlabAuthenticationError):
        return AuthenticationError(
            "GitLab authentication failed",
            error_code=E2006_GITLAB_AUTH_FAILED,
            details={"status_code": 401},
        )

    if status == 403:
        return AuthorizationError(
            "Insufficient permissions for GitLab resource",
            error_code=E2007_GITLAB_INSUFFICIENT_PERMISSIONS,
            details={"status_code": 403},
        )

    if status == 404:
        kind = not_found.kind if not_found is not None else None
        if kind is GitLabNotFoundKind.PROJECT:
            return GitLabAPIError(
                "Repository not found",
                status_code=404,
                error_code=E4001_REPO_NOT_FOUND,
                details={"status_code": 404},
            )
        if kind is GitLabNotFoundKind.FILE:
            return GitLabAPIError(
                "File not found in repository",
                status_code=404,
                error_code=E4003_FILE_NOT_FOUND,
                details={"status_code": 404},
            )
        # Default / merge_request context → PR not found
        return GitLabAPIError(
            "Merge request not found",
            status_code=404,
            error_code=E4002_PR_NOT_FOUND,
            details={"status_code": 404},
        )

    if status == 429:
        retry_after = _parse_retry_after(exc, remaining_budget)
        return RateLimitError(
            "GitLab API rate limit exceeded",
            error_code=E3006_GITLAB_RATE_LIMITED,
            details={"status_code": 429},
            retry_after=retry_after,
        )

    if status is not None and status >= 500:
        return GitLabAPIError(
            "GitLab API error occurred",
            status_code=status,
            error_code=E5021_GITLAB_API_ERROR,
            details={"status_code": status},
        )

    if isinstance(exc, (gitlab.GitlabError, requests.RequestException)):
        return GitLabAPIError(
            "GitLab API error occurred",
            status_code=status,
            error_code=E5021_GITLAB_API_ERROR,
            details={"status_code": status} if status is not None else {},
        )

    return exc


class GitLabRuntime:
    """Shared limiter + operation-scoped client factory + async blocking runner."""

    def __init__(
        self,
        config: GitLabConfig,
        private_token: str | None = None,
        *,
        base_url: str = GITLAB_COM_URL,
        limiter: anyio.CapacityLimiter | None = None,
        client_factory: Callable[..., object] | None = None,
        deadline_monotonic: float | None = None,
    ) -> None:
        self._config = config
        self._private_token = private_token
        self._base_url = (base_url or GITLAB_COM_URL).rstrip("/")
        self._limiter = limiter or anyio.CapacityLimiter(config.max_concurrent)
        self._client_factory = client_factory or gitlab.Gitlab
        self._deadline_monotonic = deadline_monotonic
        self._closed_clients = 0

    @property
    def config(self) -> GitLabConfig:
        return self._config

    @property
    def limiter(self) -> anyio.CapacityLimiter:
        return self._limiter

    @property
    def closed_client_count(self) -> int:
        """Number of operation-scoped clients closed (for tests)."""
        return self._closed_clients

    def set_deadline_monotonic(self, deadline: float) -> None:
        self._deadline_monotonic = deadline

    def remaining_budget(self) -> float:
        if self._deadline_monotonic is None:
            return float(self._config.pr_diff_request_timeout_seconds)
        return self._deadline_monotonic - time.monotonic()

    def create_client(
        self,
        *,
        remaining: float | None = None,
        base_url: str | None = None,
    ) -> object:
        """Build a fresh python-gitlab client for one operation.

        Injects max_retries and obey_rate_limit via http_request defaults
        (constructor in python-gitlab 8.5 does not accept those parameters).
        ``base_url`` selects GitLab.com or a custom-hosted instance.
        """
        budget = self.remaining_budget() if remaining is None else remaining
        if budget <= 0:
            raise DomainTimeoutError(
                "GitLab operation deadline exhausted",
                error_code=E5004_TIMEOUT_ERROR,
            )
        timeout = min(float(self._config.timeout), budget)
        url = (base_url or self._base_url or GITLAB_COM_URL).rstrip("/")
        client = self._client_factory(
            url,
            private_token=self._private_token,
            timeout=timeout,
            retry_transient_errors=self._config.retry_transient_errors,
        )
        self._install_request_defaults(client)
        return client

    def _install_request_defaults(self, client: object) -> None:
        """Ensure SDK retries use configured max_retries and obey_rate_limit."""
        original = getattr(client, "http_request", None)
        if original is None or not callable(original):
            return
        max_retries = self._config.max_retries
        obey = self._config.obey_rate_limit

        def http_request(*args: object, **kwargs: object) -> object:
            kwargs.setdefault("max_retries", max_retries)
            kwargs.setdefault("obey_rate_limit", obey)
            return original(*args, **kwargs)

        setattr(client, "http_request", http_request)

    def close_client(self, client: object) -> None:
        """Close an operation-scoped client session when possible."""
        try:
            session = getattr(client, "session", None)
            if session is not None and hasattr(session, "close"):
                session.close()
        finally:
            self._closed_clients += 1

    async def run_blocking(
        self,
        callback: Callable[[object], T],
        *,
        not_found: GitLabNotFoundContext | None = None,
    ) -> T:
        """Run a synchronous SDK callback with limiter, deadline, and fresh client.

        Uses ``abandon_on_cancel=True``; the worker always closes its client in
        ``finally`` so abandoned threads still release resources eventually.
        """
        remaining = self.remaining_budget()
        if remaining <= 0:
            raise DomainTimeoutError(
                "GitLab operation deadline exhausted",
                error_code=E5004_TIMEOUT_ERROR,
            )

        def worker() -> T:
            client = self.create_client(remaining=remaining)
            try:
                return callback(client)
            except BaseException as exc:
                mapped = map_gitlab_exception(
                    exc,
                    not_found=not_found,
                    remaining_budget=remaining,
                )
                if mapped is exc:
                    raise
                raise mapped from None
            finally:
                self.close_client(client)

        try:
            # Acquire the process-shared limiter on the async side so concurrent
            # operations never exceed config.max_concurrent, then run the
            # blocking callback (abandon_on_cancel: client closed in worker finally).
            async with self._limiter:
                with anyio.fail_after(remaining):
                    return await anyio.to_thread.run_sync(
                        worker,
                        abandon_on_cancel=True,
                    )
        except TimeoutError as exc:
            # anyio.fail_after raises builtin TimeoutError
            raise DomainTimeoutError(
                "GitLab operation timed out",
                error_code=E5004_TIMEOUT_ERROR,
            ) from exc
