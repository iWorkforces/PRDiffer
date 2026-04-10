from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.services.cache import CacheServiceInterface
from prdiffer.domain.services.pr_diff_service import PRDiffServiceInterface


class GetPRDiffUseCase:
    """Use case for getting PR diff data with automatic caching."""

    def __init__(
        self,
        pr_diff_service: PRDiffServiceInterface,
        cache_service: CacheServiceInterface,
        cache_hit_optimization_enabled: bool = False,
    ):
        self._pr_diff_service: PRDiffServiceInterface = pr_diff_service
        self._cache_service: CacheServiceInterface = cache_service
        self._cache_hit_optimization_enabled = cache_hit_optimization_enabled

    async def execute(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> PRDiff | None:
        """Execute the use case with automatic commit-based caching.

        The cache automatically invalidates when new commits are pushed to the PR,
        ensuring fresh data is always returned when the PR changes.
        """
        cache_key = self._cache_service.get_cache_key(repo_owner, repo_name, pr_number)

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
