"""Unit tests for VCS Provider Registry.

Tests VCSProviderRegistry which manages VCS provider plugins,
allowing dynamic registration and retrieval based on repository URLs.
"""

import pytest

from prdiffer.domain.vcs_provider_registry import (
    VCSProviderRegistry,
    UnsupportedProviderError,
)
from prdiffer.domain.interfaces.vcs_provider import VCSDiffRepositoryInterface


class MockVCSProvider(VCSDiffRepositoryInterface):
    """Mock VCS provider for testing."""

    def __init__(self, name: str = "mock"):
        self._name = name
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def provider_version(self) -> str:
        return "v1.0.0"

    async def initialize(self) -> None:
        self._initialized = True

    async def get_pr_diff(self, owner: str, repo: str, pr: int):
        from prdiffer.domain.entities.pr_diff import PRDiff

        return PRDiff(files=())

    async def get_latest_commit_sha(self, owner: str, repo: str, pr: int) -> str:
        return "abc123def"

    def supports_repository(self, url: str) -> bool:
        return self._name in url.lower()


class GitHubMockProvider(VCSDiffRepositoryInterface):
    """Mock GitHub provider for testing."""

    @property
    def provider_name(self) -> str:
        return "github"

    @property
    def provider_version(self) -> str:
        return "v2.0.0"

    async def initialize(self) -> None:
        pass

    async def get_pr_diff(self, owner: str, repo: str, pr: int):
        from prdiffer.domain.entities.pr_diff import PRDiff

        return PRDiff(files=())

    async def get_latest_commit_sha(self, owner: str, repo: str, pr: int) -> str:
        return "sha123"

    def supports_repository(self, url: str) -> bool:
        return "github.com" in url.lower()


class GitLabMockProvider(VCSDiffRepositoryInterface):
    """Mock GitLab provider for testing."""

    @property
    def provider_name(self) -> str:
        return "gitlab"

    @property
    def provider_version(self) -> str:
        return "v1.5.0"

    async def initialize(self) -> None:
        pass

    async def get_pr_diff(self, owner: str, repo: str, pr: int):
        from prdiffer.domain.entities.pr_diff import PRDiff

        return PRDiff(files=())

    async def get_latest_commit_sha(self, owner: str, repo: str, pr: int) -> str:
        return "sha456"

    def supports_repository(self, url: str) -> bool:
        return "gitlab.com" in url.lower()


class TestVCSProviderRegistryInitialization:
    """Test suite for VCSProviderRegistry initialization."""

    def test_registry_initialization(self):
        """Test that VCSProviderRegistry can be initialized."""
        registry = VCSProviderRegistry()

        assert registry is not None
        assert hasattr(registry, "_providers")
        assert isinstance(registry._providers, dict)

    def test_registry_initialization_empty(self):
        """Test that registry starts with empty providers dict."""
        registry = VCSProviderRegistry()

        assert len(registry._providers) == 0
        assert registry.get_provider_count() == 0


class TestVCSProviderRegistryRegisterProvider:
    """Test suite for register_provider method."""

    def test_register_single_provider(self):
        """Test registering a single provider."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("github")

        registry.register_provider(provider)

        assert registry.get_provider_count() == 1
        assert provider.provider_name in registry.list_providers()

    def test_register_multiple_providers(self):
        """Test registering multiple providers."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        gitlab = GitLabMockProvider()

        registry.register_provider(github)
        registry.register_provider(gitlab)

        assert registry.get_provider_count() == 2
        assert "github" in registry.list_providers()
        assert "gitlab" in registry.list_providers()

    def test_register_provider_overwrites(self):
        """Test that registering same provider name overwrites existing."""
        registry = VCSProviderRegistry()
        provider1 = MockVCSProvider("github")
        provider2 = MockVCSProvider("github")

        registry.register_provider(provider1)
        assert registry.get_provider("github") is provider1

        registry.register_provider(provider2)
        assert registry.get_provider("github") is provider2
        assert registry.get_provider_count() == 1

    def test_register_provider_preserves_instance(self):
        """Test that exact provider instance is stored."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("custom")

        registry.register_provider(provider)
        retrieved = registry.get_provider_by_name("custom")

        assert retrieved is provider


class TestVCSProviderRegistryUnregisterProvider:
    """Test suite for unregister_provider method."""

    def test_unregister_existing_provider(self):
        """Test unregistering an existing provider."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("github")

        registry.register_provider(provider)
        assert registry.get_provider_count() == 1

        registry.unregister_provider("github")
        assert registry.get_provider_count() == 0
        assert "github" not in registry.list_providers()

    def test_unregister_nonexistent_provider(self):
        """Test unregistering a non-existent provider doesn't raise error."""
        registry = VCSProviderRegistry()

        registry.unregister_provider("nonexistent")

        assert registry.get_provider_count() == 0

    def test_unregister_provider_from_multiple(self):
        """Test unregistering one provider from multiple registered."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        gitlab = GitLabMockProvider()

        registry.register_provider(github)
        registry.register_provider(gitlab)
        assert registry.get_provider_count() == 2

        registry.unregister_provider("github")
        assert registry.get_provider_count() == 1
        assert "github" not in registry.list_providers()
        assert "gitlab" in registry.list_providers()


class TestVCSProviderRegistryGetProvider:
    """Test suite for get_provider method."""

    def test_get_provider_by_url_github(self):
        """Test getting provider for GitHub URL."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        registry.register_provider(github)

        url = "https://github.com/owner/repo/pull/123"
        provider = registry.get_provider(url)

        assert provider is github
        assert provider.provider_name == "github"

    def test_get_provider_by_url_gitlab(self):
        """Test getting provider for GitLab URL."""
        registry = VCSProviderRegistry()
        gitlab = GitLabMockProvider()
        registry.register_provider(gitlab)

        url = "https://gitlab.com/owner/repo/merge_requests/123"
        provider = registry.get_provider(url)

        assert provider is gitlab
        assert provider.provider_name == "gitlab"

    def test_get_provider_url_not_supported(self):
        """Test that UnsupportedProviderError is raised for unsupported URL."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("custom")
        registry.register_provider(provider)

        url = "https://unknown.com/owner/repo/pull/123"

        with pytest.raises(UnsupportedProviderError) as exc_info:
            registry.get_provider(url)

        assert exc_info.value.url == url
        assert "Unsupported provider" in str(exc_info.value)

    def test_get_provider_no_providers_registered(self):
        """Test get_provider when no providers are registered."""
        registry = VCSProviderRegistry()

        url = "https://github.com/owner/repo/pull/123"

        with pytest.raises(UnsupportedProviderError):
            registry.get_provider(url)

    def test_get_provider_uses_first_matching(self):
        """Test that first matching provider is returned."""
        registry = VCSProviderRegistry()

        provider1 = MockVCSProvider("provider1")
        provider1.supports_repository = lambda url: "github" in url

        provider2 = MockVCSProvider("provider2")
        provider2.supports_repository = lambda url: "github" in url

        registry.register_provider(provider1)
        registry.register_provider(provider2)

        url = "https://github.com/owner/repo/pull/123"
        provider = registry.get_provider(url)

        assert provider is provider1

    def test_get_provider_case_insensitive(self):
        """Test that URL matching is case-insensitive (depends on implementation)."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        registry.register_provider(github)

        url_upper = "https://GITHUB.COM/owner/repo/pull/123"
        url_mixed = "https://GitHub.Com/owner/repo/pull/123"

        provider_upper = registry.get_provider(url_upper)
        provider_mixed = registry.get_provider(url_mixed)

        assert provider_upper is github
        assert provider_mixed is github


class TestVCSProviderRegistryGetProviderByName:
    """Test suite for get_provider_by_name method."""

    def test_get_provider_by_name_existing(self):
        """Test getting provider by name when it exists."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("custom")

        registry.register_provider(provider)
        retrieved = registry.get_provider_by_name("custom")

        assert retrieved is provider

    def test_get_provider_by_name_nonexistent(self):
        """Test getting provider by name when it doesn't exist."""
        registry = VCSProviderRegistry()

        retrieved = registry.get_provider_by_name("nonexistent")

        assert retrieved is None

    def test_get_provider_by_name_from_multiple(self):
        """Test getting specific provider from multiple registered."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        gitlab = GitLabMockProvider()

        registry.register_provider(github)
        registry.register_provider(gitlab)

        retrieved = registry.get_provider_by_name("gitlab")

        assert retrieved is gitlab


class TestVCSProviderRegistryListProviders:
    """Test suite for list_providers method."""

    def test_list_providers_empty(self):
        """Test listing providers when none are registered."""
        registry = VCSProviderRegistry()

        providers = registry.list_providers()

        assert isinstance(providers, list)
        assert len(providers) == 0

    def test_list_providers_single(self):
        """Test listing providers with one registered."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("github")

        registry.register_provider(provider)
        providers = registry.list_providers()

        assert len(providers) == 1
        assert "github" in providers

    def test_list_providers_multiple(self):
        """Test listing providers with multiple registered."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        gitlab = GitLabMockProvider()
        custom = MockVCSProvider("custom")

        registry.register_provider(github)
        registry.register_provider(gitlab)
        registry.register_provider(custom)

        providers = registry.list_providers()

        assert len(providers) == 3
        assert "github" in providers
        assert "gitlab" in providers
        assert "custom" in providers

    def test_list_providers_returns_list_of_strings(self):
        """Test that list_providers returns list of strings."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()

        registry.register_provider(github)
        providers = registry.list_providers()

        for provider_name in providers:
            assert isinstance(provider_name, str)


class TestVCSProviderRegistryGetProviderCount:
    """Test suite for get_provider_count method."""

    def test_get_provider_count_empty(self):
        """Test getting count when no providers registered."""
        registry = VCSProviderRegistry()

        count = registry.get_provider_count()

        assert count == 0

    def test_get_provider_count_single(self):
        """Test getting count with one provider."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("github")

        registry.register_provider(provider)
        count = registry.get_provider_count()

        assert count == 1

    def test_get_provider_count_multiple(self):
        """Test getting count with multiple providers."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        gitlab = GitLabMockProvider()
        custom = MockVCSProvider("custom")

        registry.register_provider(github)
        registry.register_provider(gitlab)
        registry.register_provider(custom)

        count = registry.get_provider_count()

        assert count == 3

    def test_get_provider_count_after_unregister(self):
        """Test count decreases after unregistering."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        gitlab = GitLabMockProvider()

        registry.register_provider(github)
        registry.register_provider(gitlab)
        assert registry.get_provider_count() == 2

        registry.unregister_provider("github")
        assert registry.get_provider_count() == 1


class TestVCSProviderRegistryClearAll:
    """Test suite for clear_all method."""

    def test_clear_all_empty(self):
        """Test clearing when registry is already empty."""
        registry = VCSProviderRegistry()

        registry.clear_all()

        assert registry.get_provider_count() == 0

    def test_clear_all_with_providers(self):
        """Test clearing all registered providers."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        gitlab = GitLabMockProvider()
        custom = MockVCSProvider("custom")

        registry.register_provider(github)
        registry.register_provider(gitlab)
        registry.register_provider(custom)
        assert registry.get_provider_count() == 3

        registry.clear_all()

        assert registry.get_provider_count() == 0
        assert registry.list_providers() == []

    def test_clear_all_can_reregister(self):
        """Test that providers can be registered after clear_all."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()

        registry.register_provider(github)
        assert registry.get_provider_count() == 1

        registry.clear_all()
        assert registry.get_provider_count() == 0

        github2 = GitHubMockProvider()
        registry.register_provider(github2)
        assert registry.get_provider_count() == 1


class TestUnsupportedProviderError:
    """Test suite for UnsupportedProviderError exception."""

    def test_unsupported_provider_error_init(self):
        """Test UnsupportedProviderError initialization."""
        url = "https://unknown.com/owner/repo/pull/123"
        error = UnsupportedProviderError(url)

        assert error.url == url
        assert "Unsupported provider" in str(error)
        assert url in str(error)

    def test_unsupported_provider_error_details(self):
        """Test that UnsupportedProviderError has details."""
        url = "https://invalid.com/owner/repo/pull/456"
        error = UnsupportedProviderError(url)

        assert hasattr(error, "details")
        assert error.details is not None
        assert error.details["url"] == url


class TestVCSProviderRegistryEdgeCases:
    """Test suite for VCSProviderRegistry edge cases."""

    def test_register_provider_with_special_name(self):
        """Test registering provider with special characters in name."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("my-provider_v2")

        registry.register_provider(provider)

        assert "my-provider_v2" in registry.list_providers()
        assert registry.get_provider_count() == 1

    def test_register_same_instance_multiple_times(self):
        """Test registering same instance multiple times (should overwrite)."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("github")

        registry.register_provider(provider)
        registry.register_provider(provider)
        registry.register_provider(provider)

        assert registry.get_provider_count() == 1
        assert registry.get_provider_by_name("github") is provider

    def test_mixed_case_provider_names(self):
        """Test provider names with different cases."""
        registry = VCSProviderRegistry()
        provider1 = MockVCSProvider("GitHub")
        provider2 = MockVCSProvider("github")
        provider3 = MockVCSProvider("GITHUB")

        registry.register_provider(provider1)
        registry.register_provider(provider2)
        registry.register_provider(provider3)

        assert registry.get_provider_count() == 3
        assert "GitHub" in registry.list_providers()
        assert "github" in registry.list_providers()
        assert "GITHUB" in registry.list_providers()

    def test_provider_with_empty_name(self):
        """Test registering provider with empty name (edge case)."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("")

        registry.register_provider(provider)

        assert "" in registry.list_providers()
        assert registry.get_provider_count() == 1

    def test_unregister_provider_empty_name(self):
        """Test unregistering provider with empty name."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("")

        registry.register_provider(provider)
        assert registry.get_provider_count() == 1

        registry.unregister_provider("")
        assert registry.get_provider_count() == 0

    def test_get_provider_by_empty_name(self):
        """Test getting provider with empty name."""
        registry = VCSProviderRegistry()
        provider = MockVCSProvider("")

        registry.register_provider(provider)
        retrieved = registry.get_provider_by_name("")

        assert retrieved is provider

    def test_url_with_query_params(self):
        """Test provider detection with URLs containing query parameters."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        registry.register_provider(github)

        url = "https://github.com/owner/repo/pull/123?param=value&other=test"
        provider = registry.get_provider(url)

        assert provider is github

    def test_url_with_fragment(self):
        """Test provider detection with URLs containing fragments."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        registry.register_provider(github)

        url = "https://github.com/owner/repo/pull/123#section"
        provider = registry.get_provider(url)

        assert provider is github

    def test_protocol_agnostic_url(self):
        """Test provider detection with different protocols."""
        registry = VCSProviderRegistry()
        github = GitHubMockProvider()
        registry.register_provider(github)

        https_url = "https://github.com/owner/repo/pull/123"
        http_url = "http://github.com/owner/repo/pull/123"

        provider_https = registry.get_provider(https_url)
        provider_http = registry.get_provider(http_url)

        assert provider_https is github
        assert provider_http is github
