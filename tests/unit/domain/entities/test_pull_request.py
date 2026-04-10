"""Unit tests for PullRequest entity.

Tests the PullRequest dataclass and PRState enum which represent GitHub pull requests.
"""

from prdiffer.domain.entities.pull_request import PullRequest, PRState


class TestPRState:
    """Test suite for PRState enumeration."""

    def test_pr_state_enum_values(self):
        """Test that PRState enum has correct values."""
        assert PRState.OPEN.value == "open"
        assert PRState.CLOSED.value == "closed"
        assert PRState.MERGED.value == "merged"

    def test_pr_state_enum_members(self):
        """Test that PRState enum has exactly three members."""
        assert len(PRState) == 3
        assert set(PRState) == {PRState.OPEN, PRState.CLOSED, PRState.MERGED}

    def test_pr_state_comparison(self):
        """Test PRState equality comparison."""
        assert PRState.OPEN == PRState.OPEN
        assert PRState.CLOSED == PRState.CLOSED
        assert PRState.MERGED == PRState.MERGED
        assert PRState.OPEN != PRState.CLOSED
        assert PRState.OPEN != PRState.MERGED
        assert PRState.CLOSED != PRState.MERGED

    def test_pr_state_string_representation(self):
        """Test PRState string values."""
        assert str(PRState.OPEN.value) == "open"
        assert str(PRState.CLOSED.value) == "closed"
        assert str(PRState.MERGED.value) == "merged"


class TestPullRequestCreation:
    """Test suite for PullRequest creation and initialization."""

    def test_pull_request_creation_with_all_fields(self):
        """Test creating a PullRequest with all fields."""
        pr = PullRequest(
            number=123,
            title="Fix bug in authentication",
            state=PRState.OPEN,
            head_sha="abc123def456",
            base_sha="def456abc123",
            head_ref="feature-branch",
            base_ref="main",
            author="johndoe",
            body="This PR fixes the authentication bug reported in issue #456",
            created_at="2024-01-01T10:00:00Z",
            updated_at="2024-01-02T15:30:00Z",
            merged_at=None,
            html_url="https://github.com/owner/repo/pull/123",
        )

        assert pr.number == 123
        assert pr.title == "Fix bug in authentication"
        assert pr.state == PRState.OPEN
        assert pr.head_sha == "abc123def456"
        assert pr.base_sha == "def456abc123"
        assert pr.head_ref == "feature-branch"
        assert pr.base_ref == "main"
        assert pr.author == "johndoe"
        assert pr.body == "This PR fixes the authentication bug reported in issue #456"
        assert pr.created_at == "2024-01-01T10:00:00Z"
        assert pr.updated_at == "2024-01-02T15:30:00Z"
        assert pr.merged_at is None
        assert pr.html_url == "https://github.com/owner/repo/pull/123"

    def test_pull_request_creation_with_minimal_fields(self):
        """Test creating a PullRequest with only required fields."""
        pr = PullRequest(
            number=123,
            title="Fix bug",
            state=PRState.OPEN,
            head_sha="abc123",
            base_sha="def456",
            head_ref="feature",
            base_ref="main",
        )

        assert pr.number == 123
        assert pr.title == "Fix bug"
        assert pr.state == PRState.OPEN
        assert pr.head_sha == "abc123"
        assert pr.base_sha == "def456"
        assert pr.head_ref == "feature"
        assert pr.base_ref == "main"
        assert pr.author is None
        assert pr.body is None
        assert pr.created_at is None
        assert pr.updated_at is None
        assert pr.merged_at is None
        assert pr.html_url is None

    def test_pull_request_creation_with_optional_fields_none(self):
        """Test creating a PullRequest with explicitly None optional fields."""
        pr = PullRequest(
            number=456,
            title="Add feature",
            state=PRState.OPEN,
            head_sha="abc",
            base_sha="def",
            head_ref="feat",
            base_ref="develop",
            author=None,
            body=None,
            created_at=None,
            updated_at=None,
            merged_at=None,
            html_url=None,
        )

        assert pr.author is None
        assert pr.body is None
        assert pr.created_at is None
        assert pr.updated_at is None
        assert pr.merged_at is None
        assert pr.html_url is None


class TestPullRequestStates:
    """Test suite for PullRequest state handling."""

    def test_pull_request_open_state(self):
        """Test PullRequest with OPEN state."""
        pr = PullRequest(
            number=1,
            title="PR",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )

        assert pr.state == PRState.OPEN
        assert pr.merged_at is None

    def test_pull_request_closed_state(self):
        """Test PullRequest with CLOSED state."""
        pr = PullRequest(
            number=2,
            title="PR",
            state=PRState.CLOSED,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )

        assert pr.state == PRState.CLOSED

    def test_pull_request_merged_state(self):
        """Test PullRequest with MERGED state."""
        pr = PullRequest(
            number=3,
            title="PR",
            state=PRState.MERGED,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
            merged_at="2024-01-03T12:00:00Z",
        )

        assert pr.state == PRState.MERGED
        assert pr.merged_at == "2024-01-03T12:00:00Z"

    def test_pull_request_state_transitions(self):
        """Test creating PullRequests with different states."""
        open_pr = PullRequest(
            number=1,
            title="Open PR",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )
        closed_pr = PullRequest(
            number=2,
            title="Closed PR",
            state=PRState.CLOSED,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )
        merged_pr = PullRequest(
            number=3,
            title="Merged PR",
            state=PRState.MERGED,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )

        assert open_pr.state == PRState.OPEN
        assert closed_pr.state == PRState.CLOSED
        assert merged_pr.state == PRState.MERGED


class TestPullRequestEquality:
    """Test suite for PullRequest equality comparison."""

    def test_pull_request_equality_identical(self):
        """Test that two PullRequest instances with same values are equal."""
        pr1 = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
            author="john",
            body="Description",
            created_at="2024-01-01T10:00:00Z",
            updated_at="2024-01-02T15:00:00Z",
            merged_at=None,
            html_url="https://github.com/owner/repo/pull/123",
        )
        pr2 = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
            author="john",
            body="Description",
            created_at="2024-01-01T10:00:00Z",
            updated_at="2024-01-02T15:00:00Z",
            merged_at=None,
            html_url="https://github.com/owner/repo/pull/123",
        )

        assert pr1 == pr2

    def test_pull_request_equality_minimal_fields(self):
        """Test equality with minimal required fields."""
        pr1 = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )
        pr2 = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )

        assert pr1 == pr2

    def test_pull_request_inequality_different_number(self):
        """Test that PullRequest instances with different numbers are not equal."""
        pr1 = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )
        pr2 = PullRequest(
            number=456,
            title="Fix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )

        assert pr1 != pr2

    def test_pull_request_inequality_different_state(self):
        """Test that PullRequest instances with different states are not equal."""
        pr1 = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )
        pr2 = PullRequest(
            number=123,
            title="Fix",
            state=PRState.CLOSED,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )

        assert pr1 != pr2

    def test_pull_request_inequality_different_sha(self):
        """Test that PullRequest instances with different SHAs are not equal."""
        pr1 = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="abc123",
            base_sha="def456",
            head_ref="h",
            base_ref="m",
        )
        pr2 = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="xyz789",
            base_sha="def456",
            head_ref="h",
            base_ref="m",
        )

        assert pr1 != pr2


class TestPullRequestAttributes:
    """Test suite for PullRequest attribute access and behavior."""

    def test_pull_request_has_required_attributes(self):
        """Test that PullRequest has all required attributes."""
        pr = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )

        assert hasattr(pr, "number")
        assert hasattr(pr, "title")
        assert hasattr(pr, "state")
        assert hasattr(pr, "head_sha")
        assert hasattr(pr, "base_sha")
        assert hasattr(pr, "head_ref")
        assert hasattr(pr, "base_ref")
        assert hasattr(pr, "author")
        assert hasattr(pr, "body")
        assert hasattr(pr, "created_at")
        assert hasattr(pr, "updated_at")
        assert hasattr(pr, "merged_at")
        assert hasattr(pr, "html_url")

    def test_pull_request_attribute_types(self):
        """Test that PullRequest attributes have correct types."""
        pr = PullRequest(
            number=123,
            title="Fix bug",
            state=PRState.OPEN,
            head_sha="abc123",
            base_sha="def456",
            head_ref="feature",
            base_ref="main",
            author="johndoe",
            body="Description",
            created_at="2024-01-01T10:00:00Z",
            updated_at="2024-01-02T15:00:00Z",
            merged_at=None,
            html_url="https://github.com/owner/repo/pull/123",
        )

        assert isinstance(pr.number, int)
        assert isinstance(pr.title, str)
        assert isinstance(pr.state, PRState)
        assert isinstance(pr.head_sha, str)
        assert isinstance(pr.base_sha, str)
        assert isinstance(pr.head_ref, str)
        assert isinstance(pr.base_ref, str)
        assert isinstance(pr.author, str)
        assert isinstance(pr.body, str)
        assert isinstance(pr.created_at, str)
        assert isinstance(pr.updated_at, str)
        assert pr.merged_at is None
        assert isinstance(pr.html_url, str)

    def test_pull_request_none_attributes_types(self):
        """Test that None attributes are properly None."""
        pr = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )

        assert pr.author is None
        assert pr.body is None
        assert pr.created_at is None
        assert pr.updated_at is None
        assert pr.merged_at is None
        assert pr.html_url is None

    def test_pull_request_string_representation(self):
        """Test PullRequest string representation includes key fields."""
        pr = PullRequest(
            number=123,
            title="Fix bug",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )

        pr_str = str(pr)
        assert "123" in pr_str or "Fix bug" in pr_str or "PullRequest" in pr_str

    def test_pull_request_repr(self):
        """Test PullRequest repr includes class name and key attributes."""
        pr = PullRequest(
            number=123,
            title="Fix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
        )

        pr_repr = repr(pr)
        assert "PullRequest" in pr_repr


class TestPullRequestTimestamps:
    """Test suite for PullRequest timestamp handling."""

    def test_pull_request_iso8601_timestamps(self):
        """Test PullRequest with ISO 8601 formatted timestamps."""
        pr = PullRequest(
            number=123,
            title="Fix",
            state=PRState.MERGED,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
            created_at="2024-01-01T10:00:00Z",
            updated_at="2024-01-02T15:30:00Z",
            merged_at="2024-01-03T12:00:00Z",
        )

        assert pr.created_at == "2024-01-01T10:00:00Z"
        assert pr.updated_at == "2024-01-02T15:30:00Z"
        assert pr.merged_at == "2024-01-03T12:00:00Z"

    def test_pull_request_merged_at_only_for_merged_prs(self):
        """Test that merged_at should typically only be set for merged PRs."""
        open_pr = PullRequest(
            number=1,
            title="Open",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
            merged_at=None,
        )
        merged_pr = PullRequest(
            number=2,
            title="Merged",
            state=PRState.MERGED,
            head_sha="a",
            base_sha="b",
            head_ref="h",
            base_ref="m",
            merged_at="2024-01-03T12:00:00Z",
        )

        assert open_pr.merged_at is None
        assert merged_pr.merged_at == "2024-01-03T12:00:00Z"


class TestPullRequestBranchReferences:
    """Test suite for PullRequest branch reference handling."""

    def test_pull_request_with_different_base_branches(self):
        """Test PullRequest targeting different base branches."""
        pr_to_main = PullRequest(
            number=1,
            title="To main",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="feature",
            base_ref="main",
        )
        pr_to_develop = PullRequest(
            number=2,
            title="To develop",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="feature",
            base_ref="develop",
        )
        pr_to_release = PullRequest(
            number=3,
            title="To release",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="hotfix",
            base_ref="release/1.0",
        )

        assert pr_to_main.base_ref == "main"
        assert pr_to_develop.base_ref == "develop"
        assert pr_to_release.base_ref == "release/1.0"

    def test_pull_request_branch_naming_patterns(self):
        """Test PullRequest with various branch naming patterns."""
        pr_feature = PullRequest(
            number=1,
            title="Feature",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="feature/new-login",
            base_ref="develop",
        )
        pr_bugfix = PullRequest(
            number=2,
            title="Bugfix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="bugfix/auth-error",
            base_ref="main",
        )
        pr_hotfix = PullRequest(
            number=3,
            title="Hotfix",
            state=PRState.OPEN,
            head_sha="a",
            base_sha="b",
            head_ref="hotfix/critical-fix",
            base_ref="main",
        )

        assert pr_feature.head_ref == "feature/new-login"
        assert pr_bugfix.head_ref == "bugfix/auth-error"
        assert pr_hotfix.head_ref == "hotfix/critical-fix"
