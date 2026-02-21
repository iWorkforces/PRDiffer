"""Unit tests for Repository entity.

Tests the Repository dataclass which represents a GitHub repository.
"""

from prdiffer.domain.entities import Repository


class TestRepositoryCreation:
    """Test suite for Repository creation and initialization."""

    def test_repository_creation_with_all_fields(self):
        """Test creating a Repository with all fields."""
        repo = Repository(
            name="myrepo",
            owner="acme",
            full_name="acme/myrepo",
            default_branch="main",
            description="Test repository",
            is_private=True,
            clone_url="https://github.com/acme/myrepo.git",
            html_url="https://github.com/acme/myrepo",
        )

        assert repo.name == "myrepo"
        assert repo.owner == "acme"
        assert repo.full_name == "acme/myrepo"
        assert repo.default_branch == "main"
        assert repo.description == "Test repository"
        assert repo.is_private is True
        assert repo.clone_url == "https://github.com/acme/myrepo.git"
        assert repo.html_url == "https://github.com/acme/myrepo"

    def test_repository_creation_with_minimal_fields(self):
        """Test creating a Repository with only required fields."""
        repo = Repository(
            name="myrepo",
            owner="acme",
            full_name="acme/myrepo",
            default_branch="main",
        )

        assert repo.name == "myrepo"
        assert repo.owner == "acme"
        assert repo.full_name == "acme/myrepo"
        assert repo.default_branch == "main"
        assert repo.description is None
        assert repo.is_private is False  # default value
        assert repo.clone_url is None
        assert repo.html_url is None

    def test_repository_creation_with_optional_fields_none(self):
        """Test creating a Repository with explicitly None optional fields."""
        repo = Repository(
            name="myrepo",
            owner="acme",
            full_name="acme/myrepo",
            default_branch="main",
            description=None,
            is_private=False,
            clone_url=None,
            html_url=None,
        )

        assert repo.description is None
        assert repo.is_private is False
        assert repo.clone_url is None
        assert repo.html_url is None

    def test_repository_creation_with_public_repo(self):
        """Test creating a public repository (is_private=False)."""
        repo = Repository(
            name="public-repo",
            owner="opensource",
            full_name="opensource/public-repo",
            default_branch="master",
            is_private=False,
        )

        assert repo.is_private is False

    def test_repository_creation_with_private_repo(self):
        """Test creating a private repository (is_private=True)."""
        repo = Repository(
            name="private-repo",
            owner="company",
            full_name="company/private-repo",
            default_branch="main",
            is_private=True,
        )

        assert repo.is_private is True

    def test_repository_with_different_default_branches(self):
        """Test Repository with various default branch names."""
        repo_main = Repository(name="repo1", owner="owner", full_name="owner/repo1", default_branch="main")
        repo_master = Repository(
            name="repo2",
            owner="owner",
            full_name="owner/repo2",
            default_branch="master",
        )
        repo_develop = Repository(
            name="repo3",
            owner="owner",
            full_name="owner/repo3",
            default_branch="develop",
        )

        assert repo_main.default_branch == "main"
        assert repo_master.default_branch == "master"
        assert repo_develop.default_branch == "develop"


class TestRepositoryEquality:
    """Test suite for Repository equality comparison."""

    def test_repository_equality_identical(self):
        """Test that two Repository instances with same values are equal."""
        repo1 = Repository(
            name="myrepo",
            owner="acme",
            full_name="acme/myrepo",
            default_branch="main",
            description="Test",
            is_private=True,
            clone_url="https://github.com/acme/myrepo.git",
            html_url="https://github.com/acme/myrepo",
        )
        repo2 = Repository(
            name="myrepo",
            owner="acme",
            full_name="acme/myrepo",
            default_branch="main",
            description="Test",
            is_private=True,
            clone_url="https://github.com/acme/myrepo.git",
            html_url="https://github.com/acme/myrepo",
        )

        assert repo1 == repo2

    def test_repository_equality_minimal_fields(self):
        """Test equality with minimal required fields."""
        repo1 = Repository(name="myrepo", owner="acme", full_name="acme/myrepo", default_branch="main")
        repo2 = Repository(name="myrepo", owner="acme", full_name="acme/myrepo", default_branch="main")

        assert repo1 == repo2

    def test_repository_inequality_different_name(self):
        """Test that Repository instances with different names are not equal."""
        repo1 = Repository(name="repo1", owner="acme", full_name="acme/repo1", default_branch="main")
        repo2 = Repository(name="repo2", owner="acme", full_name="acme/repo2", default_branch="main")

        assert repo1 != repo2

    def test_repository_inequality_different_owner(self):
        """Test that Repository instances with different owners are not equal."""
        repo1 = Repository(
            name="myrepo",
            owner="owner1",
            full_name="owner1/myrepo",
            default_branch="main",
        )
        repo2 = Repository(
            name="myrepo",
            owner="owner2",
            full_name="owner2/myrepo",
            default_branch="main",
        )

        assert repo1 != repo2

    def test_repository_inequality_different_description(self):
        """Test that Repository instances with different descriptions are not equal."""
        repo1 = Repository(
            name="myrepo",
            owner="acme",
            full_name="acme/myrepo",
            default_branch="main",
            description="Description 1",
        )
        repo2 = Repository(
            name="myrepo",
            owner="acme",
            full_name="acme/myrepo",
            default_branch="main",
            description="Description 2",
        )

        assert repo1 != repo2


class TestRepositoryAttributes:
    """Test suite for Repository attribute access and behavior."""

    def test_repository_has_required_attributes(self):
        """Test that Repository has all required attributes."""
        repo = Repository(name="myrepo", owner="acme", full_name="acme/myrepo", default_branch="main")

        assert hasattr(repo, "name")
        assert hasattr(repo, "owner")
        assert hasattr(repo, "full_name")
        assert hasattr(repo, "default_branch")
        assert hasattr(repo, "description")
        assert hasattr(repo, "is_private")
        assert hasattr(repo, "clone_url")
        assert hasattr(repo, "html_url")

    def test_repository_attribute_types(self):
        """Test that Repository attributes have correct types."""
        repo = Repository(
            name="myrepo",
            owner="acme",
            full_name="acme/myrepo",
            default_branch="main",
            description="Test repo",
            is_private=True,
            clone_url="https://github.com/acme/myrepo.git",
            html_url="https://github.com/acme/myrepo",
        )

        assert isinstance(repo.name, str)
        assert isinstance(repo.owner, str)
        assert isinstance(repo.full_name, str)
        assert isinstance(repo.default_branch, str)
        assert isinstance(repo.description, str)
        assert isinstance(repo.is_private, bool)
        assert isinstance(repo.clone_url, str)
        assert isinstance(repo.html_url, str)

    def test_repository_none_attributes_types(self):
        """Test that None attributes are properly None."""
        repo = Repository(name="myrepo", owner="acme", full_name="acme/myrepo", default_branch="main")

        assert repo.description is None
        assert repo.clone_url is None
        assert repo.html_url is None

    def test_repository_string_representation(self):
        """Test Repository string representation includes key fields."""
        repo = Repository(name="myrepo", owner="acme", full_name="acme/myrepo", default_branch="main")

        repo_str = str(repo)
        assert "myrepo" in repo_str or "acme/myrepo" in repo_str

    def test_repository_repr(self):
        """Test Repository repr includes class name and key attributes."""
        repo = Repository(name="myrepo", owner="acme", full_name="acme/myrepo", default_branch="main")

        repo_repr = repr(repo)
        assert "Repository" in repo_repr
