from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.services import CacheServiceInterface
from prdiffer.domain.services import PRDiffServiceInterface
from prdiffer.infrastructure.settings import get_settings_service


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
        
        # Performance optimization feature flags
        settings = get_settings_service()
        self._cache_hit_optimization_enabled = settings.get("performance.cache_hit_optimization_enabled", False)

    async def execute(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
    ) -> PRDiff | None:
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
        
        # Performance optimization: Optimistic cache lookup
        if self._cache_hit_optimization_enabled:
            # Try optimistic lookup first (without GitHub API call)
            cached_result, cached_commit_sha = await self._cache_service.get_optimistic(cache_key)
            
            if cached_result and cached_commit_sha:
                # Validate freshness by checking current commit SHA
                current_commit_sha = await self._pr_diff_service.get_latest_commit_sha(
                    repo_owner, repo_name, pr_number
                )
                
                if current_commit_sha and cached_commit_sha == current_commit_sha:
                    # Cache hit validated - return without additional API call
                    return cached_result
                # else: cache is stale, fall through to fetch fresh data
            # else: cache miss, fall through to fetch fresh data
        
        # Legacy path OR cache miss/stale with optimization enabled
        # Get current commit SHA to check cache validity
        current_commit_sha = await self._pr_diff_service.get_latest_commit_sha(
            repo_owner, repo_name, pr_number
        )

        if not current_commit_sha:
            return None

        cached_result = await self._cache_service.get(cache_key, current_commit_sha)
        if cached_result:
            return cached_result

        result = await self._pr_diff_service.get_pr_diff(repo_owner, repo_name, pr_number)
        if result:
            await self._cache_service.set(cache_key, current_commit_sha, result)
        return result
