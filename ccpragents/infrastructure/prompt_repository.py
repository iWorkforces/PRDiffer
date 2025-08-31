"""Prompt repository implementation with caching."""
import hashlib
import time
from typing import Dict, Optional, Any
from ccpragents.domain.entities.prompt import PRDetails, PromptRequest
from ccpragents.domain.repositories.prompt_repository import PromptRepositoryInterface
from ccpragents.infrastructure.logging.console_logger import get_logger


class PromptRepository(PromptRepositoryInterface):
    """Repository for prompt processing with caching.

    This repository follows the same caching patterns as GitHubPRDiffRepository,
    using request-based caching for prompt responses.
    """

    def __init__(self):
        """Initialize the prompt repository."""
        self._logger = get_logger()
        self._logger.info("Initializing PromptRepository", component="prompt_repository")

    async def describe_pr(self, request: PromptRequest) -> str:
        """Generate a description prompt for pull request changes.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for describing PR changes
        """
        cache_key = self._get_cache_key("describe", request)

        # Try to get from cache first
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            self._logger.info("Using cached PR description prompt", cache_key=cache_key)
            return cached_response

        # Generate prompt in XML format
        prompt = f"""<prompt type="describe_pr">
  <instruction>Describe the changes in this pull request:</instruction>
  <pr_details>
{request.get_context_string()}
  </pr_details>
  <requirements>
    <requirement>Focus on what the PR does overall</requirement>
    <requirement>Highlight key changes made</requirement>
    <requirement>Explain what problems it solves</requirement>
    <requirement>Note any notable improvements or breaking changes</requirement>
    <requirement>Be specific and actionable</requirement>
    <requirement>Avoid generic descriptions</requirement>
  </requirements>
</prompt>"""

        # Cache the response
        self._cache_response(cache_key, prompt)

        self._logger.info("Generated PR description prompt",
                        component="prompt_repository",
                        cache_key=cache_key,
                        pr_details=str(request.pr_details))
        return prompt

    async def review_pr(self, request: PromptRequest) -> str:
        """Generate a review prompt for code quality and best practices.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for reviewing PR quality
        """
        cache_key = self._get_cache_key("review", request)

        # Try to get from cache first
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            self._logger.info("Using cached PR review prompt", cache_key=cache_key)
            return cached_response

        # Generate prompt in XML format
        prompt = f"""<prompt type="review_pr">
  <instruction>Review this pull request for code quality and best practices:</instruction>
  <pr_details>
{request.get_context_string()}
  </pr_details>
  <review_categories>
    <category>Code quality and best practices</category>
    <category>Potential bugs or issues</category>
    <category>Security concerns</category>
    <category>Performance implications</category>
    <category>Maintainability and readability</category>
    <category>Test coverage considerations</category>
    <category>Documentation needs</category>
  </review_categories>
  <requirements>
    <requirement>Provide specific, actionable feedback</requirement>
    <requirement>Structure review with clear sections</requirement>
    <requirement>Prioritize most important issues first</requirement>
    <requirement>Be constructive and provide specific suggestions</requirement>
  </requirements>
</prompt>"""

        # Cache the response
        self._cache_response(cache_key, prompt)

        self._logger.info("Generated PR review prompt",
                        component="prompt_repository",
                        cache_key=cache_key,
                        pr_details=str(request.pr_details))
        return prompt

    async def update_changelog(self, request: PromptRequest) -> str:
        """Generate a changelog prompt for a pull request.

        Args:
            request: PromptRequest containing PR details and content

        Returns:
            str: Prompt for generating changelog entries
        """
        cache_key = self._get_cache_key("changelog", request)

        # Try to get from cache first
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            self._logger.info("Using cached changelog prompt", cache_key=cache_key)
            return cached_response

        # Generate prompt in XML format
        prompt = f"""<prompt type="update_changelog">
  <instruction>Generate changelog entries for this pull request:</instruction>
  <pr_details>
{request.get_context_string()}
  </pr_details>
  <changelog_categories>
    <category type="breaking">Breaking changes (marked with BREAKING CHANGE:)</category>
    <category type="feature">New features (Added:)</category>
    <category type="bug">Bug fixes (Fixed:)</category>
    <category type="performance">Performance improvements (Performance:)</category>
    <category type="docs">Documentation updates (Docs:)</category>
    <category type="dependencies">Dependency updates (Dependencies:)</category>
  </changelog_categories>
  <requirements>
    <requirement>Follow standard changelog conventions</requirement>
    <requirement>Keep entries concise but informative</requirement>
    <requirement>Group related changes when appropriate</requirement>
  </requirements>
</prompt>"""

        # Cache the response
        self._cache_response(cache_key, prompt)

        self._logger.info("Generated changelog prompt",
                        component="prompt_repository",
                        cache_key=cache_key,
                        pr_details=str(request.pr_details))
        return prompt

    def _get_cache_key(self, operation: str, request: PromptRequest) -> str:
        """Generate a cache key for the given operation and request.

        Uses a combination of operation, PR details, and content hash.
        """
        # Create content hash from all relevant content
        content = f"{request.pr_details.model_dump_json()}"
        content += f"\n{request.pr_commit_messages}"
        content += f"\n{request.pr_diff[:10000]}"  # Limit diff size for cache key

        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

        return f"prompt/{operation}/{request.pr_details.repo_owner}/{request.pr_details.repo_name}/#{request.pr_details.pr_number}/{content_hash}"

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if it exists.

        For simplicity, we're using a simple in-memory cache without commit-based invalidation
        since prompt responses don't depend on repository state changes.
        """
        if hasattr(self, '_prompt_cache'):
            cached_data = self._prompt_cache.get(cache_key)
            if cached_data:
                # Check if not expired (TTL: 1 hour)
                if time.time() - cached_data.get('timestamp', 0) < 3600:
                    return cached_data.get('response')
                else:
                    # Remove expired entry
                    del self._prompt_cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, response: str) -> None:
        """Cache the response with associated metadata."""
        if not hasattr(self, '_prompt_cache'):
            self._prompt_cache: Dict[str, Dict[str, Any]] = {}

        self._prompt_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }

        self._logger.debug("Cached prompt response", cache_key=cache_key)

    def invalidate_cache(self, pr_details: Optional[PRDetails] = None) -> None:
        """Invalidate cached responses, optionally for a specific PR.

        Args:
            pr_details: Specific PR to invalidate cache for, or None for all
        """
        if not hasattr(self, '_prompt_cache'):
            return

        if pr_details is None:
            self._prompt_cache.clear()
            self._logger.info("Cleared all prompt cache", component="prompt_repository")
        else:
            # Find and remove all cache entries for this PR
            keys_to_remove = []
            pr_identifier = f"{pr_details.repo_owner}/{pr_details.repo_name}/#{pr_details.pr_number}"

            for cache_key in self._prompt_cache.keys():
                if pr_identifier in cache_key:
                    keys_to_remove.append(cache_key)

            for key in keys_to_remove:
                del self._prompt_cache[key]

            self._logger.info("Invalidated prompt cache for PR",
                            component="prompt_repository",
                            pr_details=str(pr_details),
                            entries_removed=len(keys_to_remove))

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict[str, Any]: Cache statistics including size and performance metrics
        """
        if not hasattr(self, '_prompt_cache'):
            return {'size': 0, 'total_entries': 0}

        return {
            'size': len(self._prompt_cache),
            'total_entries': len(self._prompt_cache),
            'keys': list(self._prompt_cache.keys())
        }


# Global instance for singleton pattern
_prompt_repository: Optional[PromptRepository] = None


def get_prompt_repository() -> PromptRepository:
    """Get the global prompt repository instance (singleton pattern).

    Returns:
        PromptRepository: The global prompt repository instance
    """
    global _prompt_repository
    if _prompt_repository is None:
        _prompt_repository = PromptRepository()
    return _prompt_repository
