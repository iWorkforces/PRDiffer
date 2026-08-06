"""Request-local GitHub PR diff session with anyio thread isolation.

Synchronous PyGithub work runs via ``anyio.to_thread.run_sync`` with a
serialized CapacityLimiter (capacity 1 when parallel fetch is disabled).
"""

from __future__ import annotations

import time
from typing import Any

import anyio
import anyio.to_thread
from github import Github
from typing import Callable, ParamSpec, TypeVar
from github.PullRequest import PullRequest as PyGithubPullRequest
from github.Repository import Repository as PyGithubRepository

from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.pr_diff_cache import (
    StrictPRDiffCacheIdentity,
    github_full_diff_v2_identity,
)
from prdiffer.domain.interfaces.pr_diff_reader import PRDiffReadSessionInterface, PRDiffSnapshot
from prdiffer.domain.exceptions import PRDifferException, TimeoutError as DomainTimeoutError
from prdiffer.domain.errors import E5004_TIMEOUT_ERROR, E5009_CONFIGURATION_ERROR
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.services.pr_diff_service import GitHubPRDiffService


_P = ParamSpec("_P")
_T = TypeVar("_T")


class GitHubPRDiffSession(PRDiffReadSessionInterface):
    """One request session: one client/repo/PR metadata lookup, always closed."""

    def __init__(
        self,
        *,
        snapshot: PRDiffSnapshot,
        github_client: Github,
        repository: PyGithubRepository,
        pull_request: PyGithubPullRequest,
        service: GitHubPRDiffService,
        limiter: anyio.CapacityLimiter,
        deadline_monotonic: float,
        logger: Any | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._github_client: Github | None = github_client
        self._repository: PyGithubRepository | None = repository
        self._pull_request: PyGithubPullRequest | None = pull_request
        self._service = service
        self._limiter = limiter
        self._deadline_monotonic = deadline_monotonic
        self._logger = logger or get_logger()
        self._closed = False
        self._metadata_lookups = 1

    @property
    def snapshot(self) -> PRDiffSnapshot:
        return self._snapshot

    @property
    def cache_identity(self) -> StrictPRDiffCacheIdentity:
        """GitHub full-diff v2 key bytes + head_sha validation token."""
        snap = self._snapshot
        return github_full_diff_v2_identity(snap.owner, snap.repo, snap.pr_number, snap.head_sha)

    @property
    def metadata_lookup_count(self) -> int:
        return self._metadata_lookups

    def _remaining_budget(self) -> float:
        return self._deadline_monotonic - time.monotonic()

    def _ensure_budget(self) -> None:
        remaining = self._remaining_budget()
        if remaining <= 0:
            raise DomainTimeoutError(
                "PR diff request deadline exhausted",
                error_code=E5004_TIMEOUT_ERROR,
                details={"limit": self._deadline_monotonic},
            )

    async def _run_sync(self, func: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs) -> _T:
        """Run blocking work on a worker thread with abandon_on_cancel=False."""
        self._ensure_budget()

        def _call() -> _T:
            return func(*args, **kwargs)

        return await anyio.to_thread.run_sync(
            _call,
            abandon_on_cancel=False,
            limiter=self._limiter,
        )

    async def build_pr_diff(self) -> PRDiff:
        """Build PRDiff using the already-open session handles."""
        self._ensure_budget()

        def _build() -> PRDiff:
            # Reuse request-local repository/PR objects; avoid a second metadata lookup.
            repo = self._repository
            pr = self._pull_request
            if repo is None or pr is None:
                raise PRDifferException("Session closed", error_code=E5009_CONFIGURATION_ERROR)
            patches = self._service._generate_diff_content(repo, pr)
            return self._service._build_pr_diff_strict(patches)

        return await self._run_sync(_build)

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        # PyGithub Github client has no mandatory close; drop strong refs.
        self._pull_request = None
        self._repository = None
        self._github_client = None


class GitHubSessionPRDiffReader:
    """Session-capable reader wrapping GitHubPRDiffService."""

    def __init__(
        self,
        service: GitHubPRDiffService,
        *,
        github_timeout_seconds: int = 30,
        request_timeout_seconds: float = 180.0,
        parallel_file_fetch_enabled: bool = True,
        max_concurrent: int = 4,
        logger: Any | None = None,
    ) -> None:
        self._service = service
        self._github_timeout_seconds = github_timeout_seconds
        self._request_timeout_seconds = request_timeout_seconds
        capacity = max_concurrent if parallel_file_fetch_enabled else 1
        self._limiter = anyio.CapacityLimiter(capacity)
        self._logger = logger or get_logger()

    async def get_pr_diff(self, repo_owner: str, repo_name: str, pr_number: int, /) -> PRDiff | None:
        session = await self.open_pr_diff_session(repo_owner, repo_name, pr_number)
        try:
            return await session.build_pr_diff()
        finally:
            await session.aclose()

    async def get_latest_commit_sha(self, repo_owner: str, repo_name: str, pr_number: int, /) -> str | None:
        # Legacy surface for non-session callers; open a short session for metadata only.
        session = await self.open_pr_diff_session(repo_owner, repo_name, pr_number)
        try:
            return session.snapshot.head_sha
        finally:
            await session.aclose()

    async def open_pr_diff_session(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        /,
    ) -> GitHubPRDiffSession:
        deadline = time.monotonic() + float(self._request_timeout_seconds)

        def _open() -> tuple[Github, PyGithubRepository, PyGithubPullRequest, PRDiffSnapshot]:
            client = self._service._github_api
            if getattr(client, "_github_client", None) is None:
                raise PRDifferException(
                    "GitHub client not initialized",
                    error_code=E5009_CONFIGURATION_ERROR,
                )
            gh = client._github_client
            assert gh is not None
            repo = client._get_pygithub_repository(f"{repo_owner}/{repo_name}")
            if repo is None:
                raise PRDifferException(
                    f"Repository not found: {repo_owner}/{repo_name}",
                    error_code=E5009_CONFIGURATION_ERROR,
                )
            pr = client._get_pygithub_pull_request(repo, pr_number)
            if pr is None:
                raise PRDifferException(
                    f"Pull request not found: {repo_owner}/{repo_name}#{pr_number}",
                    error_code=E5009_CONFIGURATION_ERROR,
                )
            base_sha = str(pr.base.sha)
            head_sha = str(pr.head.sha)
            changed = getattr(pr, "changed_files", 0)
            authoritative = int(changed) if isinstance(changed, int) and not isinstance(changed, bool) else 0
            snapshot = PRDiffSnapshot(
                owner=repo_owner,
                repo=repo_name,
                pr_number=pr_number,
                base_sha=base_sha,
                head_sha=head_sha,
                authoritative_changed_files=authoritative,
            )
            return gh, repo, pr, snapshot

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise DomainTimeoutError(
                "PR diff request deadline exhausted before session open",
                error_code=E5004_TIMEOUT_ERROR,
            )

        to_thread = anyio.to_thread
        run_sync = getattr(to_thread, "run_sync")
        gh, repo, pr, snapshot = await run_sync(
            _open,
            abandon_on_cancel=False,
            limiter=self._limiter,
        )
        return GitHubPRDiffSession(
            snapshot=snapshot,
            github_client=gh,
            repository=repo,
            pull_request=pr,
            service=self._service,
            limiter=self._limiter,
            deadline_monotonic=deadline,
            logger=self._logger,
        )
