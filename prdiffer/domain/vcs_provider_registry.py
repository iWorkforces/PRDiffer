"""VCS provider registry for multi-provider support.

This module provides a registry for managing VCS provider plugins,
allowing dynamic registration and retrieval based on repository URLs.
"""

from typing import Optional
from prdiffer.domain.interfaces.vcs_provider import VCSDiffRepositoryInterface
from prdiffer.domain.exceptions import PRDifferException


class UnsupportedProviderError(PRDifferException):
    """Raised when no provider supports the given repository URL."""

    def __init__(self, url: str):
        self.url = url
        message = f"Unsupported provider for repository URL: {url}"
        super().__init__(message, details={"url": url})


class VCSProviderRegistry:
    """Registry for managing VCS provider plugins.

    Enables:
        - Dynamic provider registration
        - Automatic provider selection based on URL
        - Multi-provider support (GitHub, GitLab, Bitbucket, etc.)

    Thread-safe for concurrent provider lookups.
    """

    def __init__(self):
        self._providers: dict[str, VCSDiffRepositoryInterface] = {}

    def register_provider(self, provider: VCSDiffRepositoryInterface) -> None:
        """Register a VCS provider.

        Args:
            provider: Provider instance implementing VCSDiffRepositoryInterface

        Example:
            registry = VCSProviderRegistry()
            github = GitHubVCSRepository(...)
            gitlab = GitLabVCSRepository(...)
            registry.register_provider(github)
            registry.register_provider(gitlab)
        """
        self._providers[provider.provider_name] = provider

    def unregister_provider(self, provider_name: str) -> None:
        """Unregister a VCS provider.

        Args:
            provider_name: Name of provider to unregister
        """
        self._providers.pop(provider_name, None)

    def get_provider(self, url: str) -> VCSDiffRepositoryInterface:
        """Get provider for given repository URL.

        Iterates through registered providers and returns the first
        one that supports the URL via `supports_repository()`.

        Args:
            url: Repository URL (e.g., https://github.com/owner/repo/pull/123)

        Returns:
            VCSDiffRepositoryInterface: Matching provider instance

        Raises:
            UnsupportedProviderError: If no provider supports the URL
        """
        for provider in self._providers.values():
            if provider.supports_repository(url):
                return provider

        raise UnsupportedProviderError(url)

    def get_provider_by_name(
        self, provider_name: str
    ) -> Optional[VCSDiffRepositoryInterface]:
        """Get provider by name (explicit selection).

        Args:
            provider_name: Provider name (e.g., 'github', 'gitlab')

        Returns:
            VCSDiffRepositoryInterface: Provider instance or None if not found
        """
        return self._providers.get(provider_name)

    def list_providers(self) -> list[str]:
        """List all registered provider names.

        Returns:
            list[str]: List of provider names
        """
        return list(self._providers.keys())

    def get_provider_count(self) -> int:
        """Get count of registered providers.

        Returns:
            int: Number of registered providers
        """
        return len(self._providers)

    def clear_all(self) -> None:
        """Clear all registered providers.

        Useful for testing or resetting registry state.
        """
        self._providers.clear()
