from ccpragents.domain.entities.pr_diff import ExtraPRDiff
from ccpragents.domain.services import CacheServiceInterface
from ccpragents.domain.repositories import PRDiffRepositoryInterface


class GetPRDiffUseCase:
    def __init__(self, repository: PRDiffRepositoryInterface, cache_service: CacheServiceInterface):
        self._repository: PRDiffRepositoryInterface = repository
        self._cache_service: CacheServiceInterface = cache_service

    async def execute(self, use_cache: bool = True) -> ExtraPRDiff:
        """Execute the use case with optional caching.

        Args:
            use_cache: Whether to use caching (default: True)

        Returns:
            ExtraPRDiff: The PR diff data
        """
        if use_cache:
            cache_key = self._cache_service.get_cache_key(
                self._repository.repo_owner,
                self._repository.repo_name,
                self._repository.pr_number
            )

            # Get current commit SHA to check cache validity
            current_commit_sha = self._repository.get_latest_commit_sha()

            # Try to get from cache
            cached_result = self._cache_service.get(cache_key, current_commit_sha)
            if cached_result:
                return cached_result

            # Cache miss, fetch from GitHub and cache the result
            result = await self._repository.get_pr_diff()
            self._cache_service.set(cache_key, current_commit_sha, result)
            return result
        else:
            # Bypass cache
            return await self._repository.get_pr_diff()
