"""VCS provider interface for multi-provider support.

This interface abstracts the differences between various VCS providers
(GitHub, GitLab, Bitbucket, etc.) to enable pluggable support.
"""

from abc import ABC, abstractmethod
from prdiffer.domain.entities.pr_diff import PRDiff


class VCSDiffRepositoryInterface(ABC):
    """Interface for VCS provider diff operations.

    This abstraction enables supporting multiple VCS providers without
    modifying core application code. Providers can be registered
    and selected dynamically based on repository URL.

    Implementation Requirements:
        - Must be async-compatible
        - Must handle provider-specific error codes
        - Must support authentication
        - Must return standard PRDiff format
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name (e.g., 'github', 'gitlab', 'bitbucket').

        Returns:
            str: Provider identifier
        """
        pass

    @property
    @abstractmethod
    def provider_version(self) -> str:
        """Get provider API version.

        Returns:
            str: API version string
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize provider connection and validate access.

        Should perform:
        - Validate authentication credentials
        - Test API connectivity
        - Verify repository access

        Raises:
            RuntimeError: If initialization fails
            ConnectionError: If cannot reach provider API
        """
        pass

    @abstractmethod
    async def get_pr_diff(self, owner: str, repo: str, pr: int) -> PRDiff:
        """Get PR/MR diff from provider.

        Args:
            owner: Repository owner/organization
            repo: Repository name
            pr: Pull request/merge request number

        Returns:
            PRDiff: Complete PR diff with file context

        Raises:
            RuntimeError: If repository not accessible
            ValueError: If PR number invalid
            ConnectionError: If API call fails
        """
        pass

    @abstractmethod
    async def get_latest_commit_sha(self, owner: str, repo: str, pr: int) -> str:
        """Get latest head commit SHA for PR.

        Args:
            owner: Repository owner/organization
            repo: Repository name
            pr: Pull request/merge request number

        Returns:
            str: Latest head commit SHA
        """
        pass

    @abstractmethod
    def supports_repository(self, url: str) -> bool:
        """Check if repository URL belongs to this provider.

        Args:
            url: Repository URL (e.g., https://github.com/owner/repo/pull/123)

        Returns:
            bool: True if this provider supports the URL
        """
        pass
