"""Unit tests for VCS provider interfaces."""

import pytest
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
        from prdiffer.domain.entities.file_diff_response import (
            FileDiffResponse,
            FileStats,
        )
        from prdiffer.domain.entities.file_patch import EDIT_TYPE

        return PRDiff(
            files=(
                FileDiffResponse(
                    path="mock_file.py",
                    status=EDIT_TYPE.MODIFIED,
                    stats=FileStats(additions=1, deletions=1),
                    diff="mock diff",
                ),
            )
        )

    async def get_latest_commit_sha(self, owner: str, repo: str, pr: int) -> str:
        return "abc123def"

    def supports_repository(self, url: str) -> bool:
        return "mock" in url.lower()


class TestVCSDiffRepositoryInterface:
    """Tests for VCS provider interface."""

    def test_provider_name_property(self):
        """Provider should have a name property."""
        provider = MockVCSProvider()
        assert provider.provider_name == "mock"

    def test_provider_version_property(self):
        """Provider should have a version property."""
        provider = MockVCSProvider()
        assert provider.provider_version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Provider should be initializeable."""
        provider = MockVCSProvider()
        await provider.initialize()
        assert provider._initialized

    @pytest.mark.asyncio
    async def test_get_pr_diff(self):
        """Provider should return PR diff."""
        provider = MockVCSProvider()
        await provider.initialize()
        diff = await provider.get_pr_diff("owner", "repo", 123)
        assert len(diff.files) == 1
        assert diff.files[0].diff == "mock diff"

    @pytest.mark.asyncio
    async def test_get_latest_commit_sha(self):
        """Provider should return commit SHA."""
        provider = MockVCSProvider()
        await provider.initialize()
        sha = await provider.get_latest_commit_sha("owner", "repo", 123)
        assert sha == "abc123def"

    def test_supports_repository(self):
        """Provider should support matching URLs."""
        provider = MockVCSProvider("github")
        assert provider.supports_repository("https://mock.com/owner/repo/pull/123")
        assert not provider.supports_repository("https://other.com/owner/repo/pull/123")
