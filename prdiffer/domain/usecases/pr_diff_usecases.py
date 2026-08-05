from typing import Protocol

from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.services.cache import CacheServiceInterface


class PRDiffReader(Protocol):
    """Read the diff and current commit SHA for one pull request."""

    async def get_pr_diff(self, repo_owner: str, repo_name: str, pr_number: int, /) -> PRDiff | None:
        """Return the structured pull request diff."""
        ...

    async def get_latest_commit_sha(self, repo_owner: str, repo_name: str, pr_number: int, /) -> str | None:
        """Return the latest pull request commit SHA."""
        ...


def _is_session_reader(reader: object) -> bool:
    """Structural check for SessionPRDiffReader without hard domain→infra import.

    Inspects the concrete type (not instance attributes) so MagicMock test
    doubles do not accidentally take the session path.
    """
    method = getattr(type(reader), "open_pr_diff_session", None)
    return callable(method)


class GetPRDiffUseCase:
    """Use case for getting PR diff data with automatic caching.

    Session-capable readers (GitHub) open one request session, use
    ``snapshot.head_sha`` for cache selection, and always close the session.
    Non-session readers (e.g. GitLab) keep the legacy two-method path.
    """

    def __init__(
        self,
        pr_diff_service: PRDiffReader,
        cache_service: CacheServiceInterface,
        cache_hit_optimization_enabled: bool = False,
        *,
        cache_namespace: str | None = None,
    ):
        self._pr_diff_service: PRDiffReader = pr_diff_service
        self._cache_service: CacheServiceInterface = cache_service
        self._cache_hit_optimization_enabled = cache_hit_optimization_enabled
        self._cache_namespace = cache_namespace

    async def execute(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> PRDiff | None:
        """Execute the use case with automatic commit-based caching."""
        if _is_session_reader(self._pr_diff_service):
            return await self._execute_session_path(repo_owner, repo_name, pr_number)
        return await self._execute_legacy_path(repo_owner, repo_name, pr_number)

    async def _execute_session_path(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> PRDiff | None:
        open_session = getattr(self._pr_diff_service, "open_pr_diff_session")
        session = await open_session(repo_owner, repo_name, pr_number)
        try:
            snapshot = session.snapshot
            cache_key = self._cache_service.get_cache_key(repo_owner, repo_name, pr_number)
            if self._cache_namespace:
                cache_key = f"{self._cache_namespace}:{cache_key}"

            if self._cache_hit_optimization_enabled:
                cached_result, cached_commit_sha = await self._cache_service.get_optimistic(cache_key)
                if cached_result and cached_commit_sha and cached_commit_sha == snapshot.head_sha:
                    return cached_result

            cached_result = await self._cache_service.get(cache_key, snapshot.head_sha)
            if cached_result:
                return cached_result

            result = await session.build_pr_diff()
            if result:
                await self._cache_service.set(cache_key, snapshot.head_sha, result)
            return result
        finally:
            await session.aclose()

    async def _execute_legacy_path(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> PRDiff | None:
        """Legacy get_latest_commit_sha → cache → get_pr_diff path (GitLab)."""
        cache_key = self._cache_service.get_cache_key(repo_owner, repo_name, pr_number)
        if self._cache_namespace:
            cache_key = f"{self._cache_namespace}:{cache_key}"

        if self._cache_hit_optimization_enabled:
            cached_result, cached_commit_sha = await self._cache_service.get_optimistic(cache_key)

            if cached_result and cached_commit_sha:
                current_commit_sha = await self._pr_diff_service.get_latest_commit_sha(repo_owner, repo_name, pr_number)

                if current_commit_sha and cached_commit_sha == current_commit_sha:
                    return cached_result

        current_commit_sha = await self._pr_diff_service.get_latest_commit_sha(repo_owner, repo_name, pr_number)

        if not current_commit_sha:
            return None

        cached_result = await self._cache_service.get(cache_key, current_commit_sha)
        if cached_result:
            return cached_result

        result = await self._pr_diff_service.get_pr_diff(repo_owner, repo_name, pr_number)
        if result:
            await self._cache_service.set(cache_key, current_commit_sha, result)
        return result
