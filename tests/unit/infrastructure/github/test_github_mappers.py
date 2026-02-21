"""Unit tests for GitHub mapper functions.

Tests mapping PyGithub types to domain entities.
"""

from datetime import datetime
from unittest.mock import Mock

from prdiffer.infrastructure.github.mappers import (
    map_pygithub_repository_to_domain,
    map_pygithub_pr_to_domain,
)
from prdiffer.domain.entities import Repository, PullRequest, PRState


class TestMapPyGithubRepositoryToDomain:
    """Test suite for mapping PyGithub Repository to domain Repository."""

    def test_maps_all_fields_successfully(self):
        """Test mapping PyGithub Repository with all fields."""
        mock_owner = Mock()
        mock_owner.login = "acme"

        mock_repo = Mock()
        mock_repo.name = "myrepo"
        mock_repo.owner = mock_owner
        mock_repo.full_name = "acme/myrepo"
        mock_repo.default_branch = "main"
        mock_repo.description = "Test repository for unit tests"
        mock_repo.private = True
        mock_repo.clone_url = "https://github.com/acme/myrepo.git"
        mock_repo.html_url = "https://github.com/acme/myrepo"

        result = map_pygithub_repository_to_domain(mock_repo)

        assert isinstance(result, Repository)
        assert result.name == "myrepo"
        assert result.owner == "acme"
        assert result.full_name == "acme/myrepo"
        assert result.default_branch == "main"
        assert result.description == "Test repository for unit tests"
        assert result.is_private is True
        assert result.clone_url == "https://github.com/acme/myrepo.git"
        assert result.html_url == "https://github.com/acme/myrepo"

    def test_maps_public_repository(self):
        """Test mapping public repository (private=False)."""
        mock_owner = Mock()
        mock_owner.login = "opensource"

        mock_repo = Mock()
        mock_repo.name = "public-repo"
        mock_repo.owner = mock_owner
        mock_repo.full_name = "opensource/public-repo"
        mock_repo.default_branch = "master"
        mock_repo.description = "An open source project"
        mock_repo.private = False
        mock_repo.clone_url = "https://github.com/opensource/public-repo.git"
        mock_repo.html_url = "https://github.com/opensource/public-repo"

        result = map_pygithub_repository_to_domain(mock_repo)

        assert result.is_private is False

    def test_handles_none_description(self):
        """Test mapping repository with None description."""
        mock_owner = Mock()
        mock_owner.login = "acme"

        mock_repo = Mock()
        mock_repo.name = "myrepo"
        mock_repo.owner = mock_owner
        mock_repo.full_name = "acme/myrepo"
        mock_repo.default_branch = "main"
        mock_repo.description = None
        mock_repo.private = False
        mock_repo.clone_url = None
        mock_repo.html_url = None

        result = map_pygithub_repository_to_domain(mock_repo)

        assert result.description is None
        assert result.clone_url is None
        assert result.html_url is None

    def test_handles_none_optional_fields(self):
        """Test mapping with all None optional fields."""
        mock_owner = Mock()
        mock_owner.login = "owner"

        mock_repo = Mock()
        mock_repo.name = "repo"
        mock_repo.owner = mock_owner
        mock_repo.full_name = "owner/repo"
        mock_repo.default_branch = "main"
        mock_repo.description = None
        mock_repo.private = False
        mock_repo.clone_url = None
        mock_repo.html_url = None

        result = map_pygithub_repository_to_domain(mock_repo)

        assert isinstance(result, Repository)
        assert result.description is None
        assert result.is_private is False
        assert result.clone_url is None
        assert result.html_url is None

    def test_maps_different_default_branches(self):
        """Test mapping repositories with different default branches."""
        mock_owner = Mock()
        mock_owner.login = "owner"

        for branch_name in ["main", "master", "develop", "trunk"]:
            mock_repo = Mock()
            mock_repo.name = "repo"
            mock_repo.owner = mock_owner
            mock_repo.full_name = "owner/repo"
            mock_repo.default_branch = branch_name
            mock_repo.description = None
            mock_repo.private = False
            mock_repo.clone_url = None
            mock_repo.html_url = None

            result = map_pygithub_repository_to_domain(mock_repo)
            assert result.default_branch == branch_name


class TestMapPyGithubPRToDomain:
    """Test suite for mapping PyGithub PullRequest to domain PullRequest."""

    def test_maps_open_pull_request_with_all_fields(self):
        """Test mapping open pull request with all fields."""
        mock_user = Mock()
        mock_user.login = "johndoe"

        mock_head = Mock()
        mock_head.sha = "abc123def456"
        mock_head.ref = "feature-branch"

        mock_base = Mock()
        mock_base.sha = "def456abc123"
        mock_base.ref = "main"

        created_at = datetime(2024, 1, 1, 10, 0, 0)
        updated_at = datetime(2024, 1, 2, 15, 30, 0)

        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.title = "Fix authentication bug"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.head = mock_head
        mock_pr.base = mock_base
        mock_pr.user = mock_user
        mock_pr.body = "This PR fixes the authentication bug"
        mock_pr.created_at = created_at
        mock_pr.updated_at = updated_at
        mock_pr.merged_at = None
        mock_pr.html_url = "https://github.com/owner/repo/pull/123"

        result = map_pygithub_pr_to_domain(mock_pr)

        assert isinstance(result, PullRequest)
        assert result.number == 123
        assert result.title == "Fix authentication bug"
        assert result.state == PRState.OPEN
        assert result.head_sha == "abc123def456"
        assert result.base_sha == "def456abc123"
        assert result.head_ref == "feature-branch"
        assert result.base_ref == "main"
        assert result.author == "johndoe"
        assert result.body == "This PR fixes the authentication bug"
        assert result.created_at == "2024-01-01T10:00:00"
        assert result.updated_at == "2024-01-02T15:30:00"
        assert result.merged_at is None
        assert result.html_url == "https://github.com/owner/repo/pull/123"

    def test_maps_merged_pull_request(self):
        """Test mapping merged pull request (merged=True takes precedence)."""
        mock_user = Mock()
        mock_user.login = "contributor"

        mock_head = Mock()
        mock_head.sha = "abc123"
        mock_head.ref = "feature"

        mock_base = Mock()
        mock_base.sha = "def456"
        mock_base.ref = "main"

        merged_at = datetime(2024, 1, 3, 12, 0, 0)

        mock_pr = Mock()
        mock_pr.number = 456
        mock_pr.title = "Add new feature"
        mock_pr.state = "closed"
        mock_pr.merged = True
        mock_pr.head = mock_head
        mock_pr.base = mock_base
        mock_pr.user = mock_user
        mock_pr.body = "New feature implementation"
        mock_pr.created_at = datetime(2024, 1, 1, 10, 0, 0)
        mock_pr.updated_at = datetime(2024, 1, 2, 15, 0, 0)
        mock_pr.merged_at = merged_at
        mock_pr.html_url = "https://github.com/owner/repo/pull/456"

        result = map_pygithub_pr_to_domain(mock_pr)

        assert result.state == PRState.MERGED
        assert result.merged_at == "2024-01-03T12:00:00"

    def test_maps_closed_pull_request(self):
        """Test mapping closed (not merged) pull request."""
        mock_head = Mock()
        mock_head.sha = "abc123"
        mock_head.ref = "feature"

        mock_base = Mock()
        mock_base.sha = "def456"
        mock_base.ref = "main"

        mock_pr = Mock()
        mock_pr.number = 789
        mock_pr.title = "Abandoned feature"
        mock_pr.state = "closed"
        mock_pr.merged = False
        mock_pr.head = mock_head
        mock_pr.base = mock_base
        mock_pr.user = None
        mock_pr.body = None
        mock_pr.created_at = None
        mock_pr.updated_at = None
        mock_pr.merged_at = None
        mock_pr.html_url = None

        result = map_pygithub_pr_to_domain(mock_pr)

        assert result.state == PRState.CLOSED
        assert result.merged_at is None

    def test_handles_none_user(self):
        """Test mapping pull request with None user."""
        mock_head = Mock()
        mock_head.sha = "abc"
        mock_head.ref = "h"

        mock_base = Mock()
        mock_base.sha = "def"
        mock_base.ref = "m"

        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.title = "PR without author"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.head = mock_head
        mock_pr.base = mock_base
        mock_pr.user = None
        mock_pr.body = None
        mock_pr.created_at = None
        mock_pr.updated_at = None
        mock_pr.merged_at = None
        mock_pr.html_url = None

        result = map_pygithub_pr_to_domain(mock_pr)

        assert result.author is None

    def test_handles_none_optional_fields(self):
        """Test mapping with all None optional fields."""
        mock_head = Mock()
        mock_head.sha = "abc"
        mock_head.ref = "feature"

        mock_base = Mock()
        mock_base.sha = "def"
        mock_base.ref = "main"

        mock_pr = Mock()
        mock_pr.number = 999
        mock_pr.title = "Minimal PR"
        mock_pr.state = "open"
        mock_pr.merged = False
        mock_pr.head = mock_head
        mock_pr.base = mock_base
        mock_pr.user = None
        mock_pr.body = None
        mock_pr.created_at = None
        mock_pr.updated_at = None
        mock_pr.merged_at = None
        mock_pr.html_url = None

        result = map_pygithub_pr_to_domain(mock_pr)

        assert isinstance(result, PullRequest)
        assert result.author is None
        assert result.body is None
        assert result.created_at is None
        assert result.updated_at is None
        assert result.merged_at is None
        assert result.html_url is None

    def test_timestamp_iso8601_formatting(self):
        """Test that datetime objects are converted to ISO 8601 strings."""
        mock_head = Mock()
        mock_head.sha = "abc"
        mock_head.ref = "feature"

        mock_base = Mock()
        mock_base.sha = "def"
        mock_base.ref = "main"

        created = datetime(2024, 12, 25, 13, 45, 30)
        updated = datetime(2024, 12, 26, 9, 15, 20)
        merged = datetime(2024, 12, 27, 11, 30, 45)

        mock_pr = Mock()
        mock_pr.number = 100
        mock_pr.title = "Test timestamps"
        mock_pr.state = "closed"
        mock_pr.merged = True
        mock_pr.head = mock_head
        mock_pr.base = mock_base
        mock_pr.user = None
        mock_pr.body = None
        mock_pr.created_at = created
        mock_pr.updated_at = updated
        mock_pr.merged_at = merged
        mock_pr.html_url = None

        result = map_pygithub_pr_to_domain(mock_pr)

        assert result.created_at == "2024-12-25T13:45:30"
        assert result.updated_at == "2024-12-26T09:15:20"
        assert result.merged_at == "2024-12-27T11:30:45"

    def test_state_logic_priority(self):
        """Test that merged flag takes priority over state field."""
        mock_head = Mock()
        mock_head.sha = "a"
        mock_head.ref = "f"

        mock_base = Mock()
        mock_base.sha = "b"
        mock_base.ref = "m"

        mock_pr_merged = Mock()
        mock_pr_merged.number = 1
        mock_pr_merged.title = "Merged"
        mock_pr_merged.state = "closed"
        mock_pr_merged.merged = True
        mock_pr_merged.head = mock_head
        mock_pr_merged.base = mock_base
        mock_pr_merged.user = None
        mock_pr_merged.body = None
        mock_pr_merged.created_at = None
        mock_pr_merged.updated_at = None
        mock_pr_merged.merged_at = None
        mock_pr_merged.html_url = None

        mock_pr_closed = Mock()
        mock_pr_closed.number = 2
        mock_pr_closed.title = "Closed"
        mock_pr_closed.state = "closed"
        mock_pr_closed.merged = False
        mock_pr_closed.head = mock_head
        mock_pr_closed.base = mock_base
        mock_pr_closed.user = None
        mock_pr_closed.body = None
        mock_pr_closed.created_at = None
        mock_pr_closed.updated_at = None
        mock_pr_closed.merged_at = None
        mock_pr_closed.html_url = None

        result_merged = map_pygithub_pr_to_domain(mock_pr_merged)
        result_closed = map_pygithub_pr_to_domain(mock_pr_closed)

        assert result_merged.state == PRState.MERGED
        assert result_closed.state == PRState.CLOSED

    def test_different_branch_patterns(self):
        """Test mapping PRs with various branch naming patterns."""
        branch_patterns = [
            ("feature/new-login", "develop"),
            ("bugfix/auth-error", "main"),
            ("hotfix/critical-fix", "release/1.0"),
            ("refactor/cleanup", "master"),
        ]

        for head_ref, base_ref in branch_patterns:
            mock_head = Mock()
            mock_head.sha = "abc"
            mock_head.ref = head_ref

            mock_base = Mock()
            mock_base.sha = "def"
            mock_base.ref = base_ref

            mock_pr = Mock()
            mock_pr.number = 100
            mock_pr.title = "Test"
            mock_pr.state = "open"
            mock_pr.merged = False
            mock_pr.head = mock_head
            mock_pr.base = mock_base
            mock_pr.user = None
            mock_pr.body = None
            mock_pr.created_at = None
            mock_pr.updated_at = None
            mock_pr.merged_at = None
            mock_pr.html_url = None

            result = map_pygithub_pr_to_domain(mock_pr)
            assert result.head_ref == head_ref
            assert result.base_ref == base_ref
