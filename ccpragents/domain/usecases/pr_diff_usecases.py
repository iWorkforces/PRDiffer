from typing import Optional
from ccpragents.domain.entities.pr_diff import PRDiff
from ccpragents.domain.services import CacheServiceInterface
from ccpragents.domain.services import PRDiffServiceInterface


class GetPRDiffUseCase:
    """Use case for getting PR diff data with automatic caching."""

    def __init__(
        self,
        pr_diff_service: PRDiffServiceInterface,
        cache_service: CacheServiceInterface,
    ):
        """Initialize the use case with dependencies.

        Args:
            pr_diff_service: Service for PR diff operations
            cache_service: Service for caching operations
        """
        self._pr_diff_service: PRDiffServiceInterface = pr_diff_service
        self._cache_service: CacheServiceInterface = cache_service

    async def execute(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> Optional[PRDiff]:
        """Execute the use case with automatic commit-based caching.

        The cache automatically invalidates when new commits are pushed to the PR,
        ensuring fresh data is always returned when the PR changes.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            Optional[PRDiff]: The PR diff data if successful, None otherwise
        """
        cache_key = self._cache_service.get_cache_key(repo_owner, repo_name, pr_number)

        # Get current commit SHA to check cache validity
        current_commit_sha = self._pr_diff_service.get_latest_commit_sha(
            repo_owner, repo_name, pr_number
        )

        if not current_commit_sha:
            return None

        # Try to get from cache
        cached_result = self._cache_service.get(cache_key, current_commit_sha)
        if cached_result:
            return cached_result

        # Cache miss, fetch from service and cache the result
        result = await self._pr_diff_service.get_pr_diff(repo_owner, repo_name, pr_number)
        if result:
            self._cache_service.set(cache_key, current_commit_sha, result)
        return result
