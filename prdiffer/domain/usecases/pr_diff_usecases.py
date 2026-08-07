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

    Session-capable readers open one request session, use
    ``session.cache_identity`` for cache selection, and always close the session.
    Non-session readers keep the legacy two-method path.
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
        *,
        base_url: str | None = None,
    ) -> PRDiff | None:
        """Execute the use case with automatic commit-based caching.

        ``base_url`` is optional and used by GitLab session readers for
        custom-hosted instances (e.g. ``https://gitlab.example.com``).
        """
        if _is_session_reader(self._pr_diff_service):
            return await self._execute_session_path(repo_owner, repo_name, pr_number, base_url=base_url)
        return await self._execute_legacy_path(repo_owner, repo_name, pr_number)

    async def _execute_session_path(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        *,
        base_url: str | None = None,
    ) -> PRDiff | None:
        from prdiffer.domain.entities.pr_diff_cache import (
            unwrap_pr_diff_cache_value,
            wrap_pr_diff_for_cache,
        )

        open_session = getattr(self._pr_diff_service, "open_pr_diff_session")
        # All session readers accept base_url (GitHub ignores; GitLab uses it).
        # Call exactly once — never swallow TypeError or probe signatures.
        session = await open_session(repo_owner, repo_name, pr_number, base_url=base_url)
        try:
            identity = session.cache_identity
            # Provider-neutral key from session; ignore cache_namespace on strict path.
            cache_key = identity.cache_key
            validation_token = identity.validation_token

            if self._cache_hit_optimization_enabled:
                cached_result, cached_token = await self._cache_service.get_optimistic(cache_key)
                unwrapped = unwrap_pr_diff_cache_value(cached_result, key=cache_key, identity=identity) if cached_result is not None else None
                if unwrapped is not None and cached_token and cached_token == validation_token:
                    return unwrapped

            cached_result = await self._cache_service.get(cache_key, validation_token)
            unwrapped = unwrap_pr_diff_cache_value(cached_result, key=cache_key, identity=identity) if cached_result is not None else None
            if unwrapped is not None:
                return unwrapped

            result = await session.build_pr_diff()
            # Use identity check so authoritative empty PRDiff(files=()) still caches.
            if result is not None:
                _ = wrap_pr_diff_for_cache(result)  # validate constructibility
                await self._cache_service.set(cache_key, validation_token, result)
            return result
        finally:
            await session.aclose()

    async def _execute_legacy_path(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> PRDiff | None:
        """Legacy get_latest_commit_sha → cache → get_pr_diff path (non-session readers)."""
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
