"""Unit tests for GitHubPRDiffRepository.

Comprehensive tests covering initialization, GitHub API interactions,
diff retrieval, PR approval, and error handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from github.GithubException import (
    GithubException,
    UnknownObjectException,
    RateLimitExceededException,
)

from prdiffer.infrastructure.github_repository import (
    GitHubPRDiffRepository,
    get_github_repository,
    _repository_cache,
)
from prdiffer.domain.exceptions import PRDifferException
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.entities.file_patch import EDIT_TYPE


@pytest.fixture(autouse=True)
def clear_repository_cache():
    """Clear repository cache before and after each test."""
    _repository_cache.clear()
    yield
    _repository_cache.clear()


@pytest.fixture
def mock_settings():
    """Create mock settings service."""
    settings = Mock()
    settings.get_github_settings.return_value = {
        "rate_limit": 5000,
        "timeout": 30,
        "max_retries": 3,
        "retry_delay": 1,
        "ignore_patterns": [],
        "valid_extensions": [],
        "retry_on_404": False,
        "retry_on_403": True,
        "retry_on_500": True,
        "retry_log_level": "DEBUG",
        "permanent_failure_log_level": "INFO",
        "circuit_breaker_enabled": True,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_timeout": 60.0,
        "adaptive_retry_enabled": True,
        "max_adaptive_delay": 30.0,
        "api_health_tracking": True,
        "context_aware_retry": True,
        "use_advanced_retry": True,
        "diff_parallel_enabled": True,
        "diff_parallel_threshold": 3,
        "diff_max_workers": 4,
        "diff_worker_timeout": 30.0,
    }
    settings.get_app_settings.return_value = {
        "max_files_allowed": 50,
    }
    settings.get.side_effect = lambda key, default=None: {
        "file_processing.parallel_fetch_threshold": 10,
        "file_processing.concurrent_downloads": 3,
        "diff.truncate_enabled": False,
        "diff.max_total_chars": 600000,
        "diff.truncation_notice": "[DIFF TRUNCATED]",
    }.get(key, default)
    return settings


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    logger = Mock()
    logger.should_log.return_value = False
    return logger


@pytest.fixture
def mock_input_validator():
    """Create mock input validator."""
    validator = Mock()
    validator.sanitize_for_logging.side_effect = lambda s, max_length=None: s[:max_length] if max_length else s
    validator.validate_github_url.return_value = ("owner", "repo", 123)
    return validator


@pytest.fixture
def mock_github_api_client():
    """Create mock GitHub API client."""
    client = Mock()
    client.initialize_client = Mock()
    client._get_pygithub_repository = Mock()
    client._get_pygithub_pull_request = Mock()
    return client


@pytest.fixture
def mock_file_processor():
    """Create mock file processor."""
    processor = Mock()
    processor.get_pr_files = AsyncMock(return_value=[])
    processor.filter_files = Mock(return_value=[])
    processor.process_files_to_patches = Mock(return_value=[])
    return processor


@pytest.fixture
def mock_diff_generator():
    """Create mock diff generator."""
    generator = Mock()
    generator.generate_extended_diff = Mock(return_value=[])
    return generator


@pytest.fixture
def repository(
    mock_settings,
    mock_logger,
    mock_input_validator,
    mock_github_api_client,
    mock_file_processor,
    mock_diff_generator,
):
    """Create GitHubPRDiffRepository instance with mocked dependencies."""
    with (
        patch(
            "prdiffer.infrastructure.github_repository.get_github_api_client",
            return_value=mock_github_api_client,
        ),
        patch(
            "prdiffer.infrastructure.github_repository.get_file_processor",
            return_value=mock_file_processor,
        ),
        patch(
            "prdiffer.infrastructure.github_repository.get_diff_generator",
            return_value=mock_diff_generator,
        ),
        patch(
            "prdiffer.infrastructure.github_repository.get_pattern_matcher",
            return_value=Mock(),
        ),
        patch(
            "prdiffer.infrastructure.github_repository.get_diff_utils",
            return_value=Mock(),
        ),
    ):
        repo = GitHubPRDiffRepository(
            repo_owner="owner",
            repo_name="repo",
            pr_number=123,
            github_token="test-token",
            settings_service=mock_settings,
            logger=mock_logger,
            input_validator=mock_input_validator,
        )
        # Attach mocks for test access
        repo._mock_api_client = mock_github_api_client
        repo._mock_file_processor = mock_file_processor
        repo._mock_diff_generator = mock_diff_generator
        return repo


class TestGitHubPRDiffRepositoryInit:
    """Tests for repository initialization."""

    def test_init_with_all_parameters(self, mock_settings, mock_logger, mock_input_validator):
        """Test initialization with all parameters."""
        with (
            patch("prdiffer.infrastructure.github_repository.get_github_api_client") as mock_get_client,
            patch("prdiffer.infrastructure.github_repository.get_file_processor"),
            patch("prdiffer.infrastructure.github_repository.get_diff_generator"),
            patch("prdiffer.infrastructure.github_repository.get_pattern_matcher"),
            patch("prdiffer.infrastructure.github_repository.get_diff_utils"),
        ):
            mock_get_client.return_value = Mock()

            repo = GitHubPRDiffRepository(
                repo_owner="owner",
                repo_name="repo",
                pr_number=456,
                github_token="token123",
                settings_service=mock_settings,
                logger=mock_logger,
                input_validator=mock_input_validator,
            )

            assert repo.repo_owner == "owner"
            assert repo.repo_name == "repo"
            assert repo.pr_number == 456
            assert repo.github_token == "token123"

    def test_init_uses_env_token_if_not_provided(self, mock_settings, mock_logger, mock_input_validator, monkeypatch):
        """Test that GITHUB_TOKEN env var is used if token not provided."""
        monkeypatch.setenv("GITHUB_TOKEN", "env-token")

        with (
            patch("prdiffer.infrastructure.github_repository.get_github_api_client") as mock_get_client,
            patch("prdiffer.infrastructure.github_repository.get_file_processor"),
            patch("prdiffer.infrastructure.github_repository.get_diff_generator"),
            patch("prdiffer.infrastructure.github_repository.get_pattern_matcher"),
            patch("prdiffer.infrastructure.github_repository.get_diff_utils"),
        ):
            mock_get_client.return_value = Mock()

            repo = GitHubPRDiffRepository(
                repo_owner="owner",
                repo_name="repo",
                pr_number=123,
                settings_service=mock_settings,
                logger=mock_logger,
                input_validator=mock_input_validator,
            )

            assert repo.github_token == "env-token"


class TestGitHubPRDiffRepositoryProperties:
    """Tests for repository properties."""

    def test_repo_owner_property(self, repository):
        """Test repo_owner property returns correct value."""
        assert repository.repo_owner == "owner"

    def test_repo_name_property(self, repository):
        """Test repo_name property returns correct value."""
        assert repository.repo_name == "repo"

    def test_pr_number_property(self, repository):
        """Test pr_number property returns correct value."""
        assert repository.pr_number == 123


class TestGitHubPRDiffRepositoryInitialize:
    """Tests for the initialize method."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, repository):
        """Test successful initialization."""
        mock_repo = Mock()
        mock_pr = Mock()
        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        await repository.initialize()

        assert repository._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_repository_not_found(self, repository):
        """Test initialization fails when repository not found."""
        repository._mock_api_client._get_pygithub_repository.side_effect = UnknownObjectException(404, "Not found")

        with pytest.raises(PRDifferException) as exc_info:
            await repository.initialize()

        assert "Failed to initialize repository" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_rate_limit_exceeded(self, repository):
        """Test initialization fails when rate limit exceeded."""
        repository._mock_api_client._get_pygithub_repository.side_effect = RateLimitExceededException(403, "Rate limit")

        with pytest.raises(PRDifferException) as exc_info:
            await repository.initialize()

        assert "Failed to initialize repository" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_github_exception(self, repository):
        """Test initialization fails on generic GitHub exception."""
        repository._mock_api_client._get_pygithub_repository.side_effect = GithubException(500, "Server error")

        with pytest.raises(PRDifferException) as exc_info:
            await repository.initialize()

        assert "GitHub API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_pr_not_found(self, repository):
        """Test initialization fails when PR not found."""
        mock_repo = Mock()
        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.side_effect = UnknownObjectException(404, "PR not found")

        with pytest.raises(PRDifferException) as exc_info:
            await repository.initialize()

        assert "Failed to initialize pull request" in str(exc_info.value)


class TestGitHubPRDiffRepositoryGetLatestCommitSha:
    """Tests for get_latest_commit_sha method."""

    @pytest.mark.asyncio
    async def test_get_latest_commit_sha_success(self, repository):
        """Test getting latest commit SHA successfully."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.head.sha = "abc123def456"
        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        sha = await repository.get_latest_commit_sha()

        assert sha == "abc123def456"

    @pytest.mark.asyncio
    async def test_get_latest_commit_sha_not_initialized(self, repository):
        """Test getting SHA fails when not initialized."""
        repository._mock_api_client._get_pygithub_repository.side_effect = UnknownObjectException(404, "Not found")

        with pytest.raises(PRDifferException):
            await repository.get_latest_commit_sha()


class TestGitHubPRDiffRepositoryGetPRDiff:
    """Tests for get_pr_diff method."""

    @pytest.mark.asyncio
    async def test_get_pr_diff_success(self, repository):
        """Test getting PR diff successfully."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.base.sha = "base123"
        mock_pr.head.sha = "head123"
        mock_pr.get_files.return_value = []

        # Mock compare for merge base
        mock_compare = Mock()
        mock_compare.merge_base_commit.sha = "merge123"
        mock_repo.compare.return_value = mock_compare

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        # Create sample file patch
        from prdiffer.domain.entities.file_patch import FilePatchInfo

        file_patch = FilePatchInfo(
            filename="test.py",
            patch="diff content",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=5,
            num_minus_lines=2,
        )
        repository._mock_file_processor.process_files_to_patches.return_value = [file_patch]

        result = await repository.get_pr_diff()

        assert isinstance(result, PRDiff)
        assert isinstance(result.files, tuple)

    @pytest.mark.asyncio
    async def test_get_pr_diff_not_initialized(self, repository):
        """Test getting diff fails when not initialized."""
        repository._mock_api_client._get_pygithub_repository.side_effect = UnknownObjectException(404, "Not found")

        with pytest.raises(PRDifferException):
            await repository.get_pr_diff()


class TestGitHubPRDiffRepositoryApprovePR:
    """Tests for approve_pr_with_comment method."""

    @pytest.mark.asyncio
    async def test_approve_pr_success(self, repository):
        """Test approving PR successfully."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_review = Mock()
        mock_review.id = "review123"
        mock_pr.create_review.return_value = mock_review

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        result = await repository.approve_pr_with_comment("https://github.com/owner/repo/pull/123", "Great work!")

        assert "Successfully approved PR" in result
        mock_pr.create_review.assert_called_once_with(event="APPROVE", body="Great work!")

    @pytest.mark.asyncio
    async def test_approve_pr_empty_compliment(self, repository):
        """Test approving PR with empty compliment fails."""
        with pytest.raises(ValueError, match="Compliment cannot be empty"):
            await repository.approve_pr_with_comment("https://github.com/owner/repo/pull/123", "")

    @pytest.mark.asyncio
    async def test_approve_pr_non_string_compliment(self, repository):
        """Test approving PR with non-string compliment fails."""
        with pytest.raises(ValueError, match="Compliment must be a string"):
            await repository.approve_pr_with_comment("https://github.com/owner/repo/pull/123", 123)

    @pytest.mark.asyncio
    async def test_approve_pr_404_error(self, repository):
        """Test approving PR handles 404 error."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.create_review.side_effect = GithubException(404, "Not found")

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        with pytest.raises(RuntimeError, match="not found"):
            await repository.approve_pr_with_comment("https://github.com/owner/repo/pull/123", "Great!")

    @pytest.mark.asyncio
    async def test_approve_pr_403_error(self, repository):
        """Test approving PR handles 403 forbidden error."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.create_review.side_effect = GithubException(403, "Forbidden")

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        with pytest.raises(RuntimeError, match="Insufficient permissions"):
            await repository.approve_pr_with_comment("https://github.com/owner/repo/pull/123", "Great!")

    @pytest.mark.asyncio
    async def test_approve_pr_rate_limit_error(self, repository):
        """Test approving PR handles rate limit error."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.create_review.side_effect = GithubException(429, "Rate limit exceeded")

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            await repository.approve_pr_with_comment("https://github.com/owner/repo/pull/123", "Great!")

    @pytest.mark.asyncio
    async def test_approve_pr_generic_error(self, repository):
        """Test approving PR handles generic GitHub error."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.create_review.side_effect = GithubException(500, "Server error")

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        with pytest.raises(RuntimeError, match="GitHub API error"):
            await repository.approve_pr_with_comment("https://github.com/owner/repo/pull/123", "Great!")


class TestGitHubPRDiffRepositoryUpdatePRDescription:
    """Tests for update_pr_description method."""

    @pytest.mark.asyncio
    async def test_update_pr_description_success(self, repository):
        """Test updating PR description successfully."""
        mock_repo = Mock()
        mock_pr = Mock()

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        result = await repository.update_pr_description("https://github.com/owner/repo/pull/123", "New description text")

        assert "Successfully updated description" in result
        mock_pr.edit.assert_called_once_with(body="New description text")

    @pytest.mark.asyncio
    async def test_update_pr_description_empty_description(self, repository):
        """Test updating PR description with empty description fails."""
        with pytest.raises(ValueError, match="Description cannot be empty"):
            await repository.update_pr_description("https://github.com/owner/repo/pull/123", "")

    @pytest.mark.asyncio
    async def test_update_pr_description_non_string_description(self, repository):
        """Test updating PR description with non-string description fails."""
        with pytest.raises(ValueError, match="Description must be a string"):
            await repository.update_pr_description("https://github.com/owner/repo/pull/123", 123)

    @pytest.mark.asyncio
    async def test_update_pr_description_404_error(self, repository):
        """Test updating PR description handles 404 error."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.edit.side_effect = GithubException(404, "Not found")

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        with pytest.raises(RuntimeError, match="not found"):
            await repository.update_pr_description("https://github.com/owner/repo/pull/123", "New description")

    @pytest.mark.asyncio
    async def test_update_pr_description_403_error(self, repository):
        """Test updating PR description handles 403 forbidden error."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.edit.side_effect = GithubException(403, "Forbidden")

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        with pytest.raises(RuntimeError, match="Insufficient permissions"):
            await repository.update_pr_description("https://github.com/owner/repo/pull/123", "New description")

    @pytest.mark.asyncio
    async def test_update_pr_description_rate_limit_error(self, repository):
        """Test updating PR description handles rate limit error."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.edit.side_effect = GithubException(429, "Rate limit exceeded")

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            await repository.update_pr_description("https://github.com/owner/repo/pull/123", "New description")

    @pytest.mark.asyncio
    async def test_update_pr_description_generic_error(self, repository):
        """Test updating PR description handles generic GitHub error."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.edit.side_effect = GithubException(500, "Server error")

        repository._mock_api_client._get_pygithub_repository.return_value = mock_repo
        repository._mock_api_client._get_pygithub_pull_request.return_value = mock_pr

        with pytest.raises(RuntimeError, match="GitHub API error"):
            await repository.update_pr_description("https://github.com/owner/repo/pull/123", "New description")


class TestGitHubPRDiffRepositoryGetMergeBaseCommits:
    """Tests for _get_merge_base_commits method."""

    async def test_get_merge_base_commits_success(self, repository):
        """Test getting merge base commits successfully."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.base.sha = "base123"
        mock_pr.head.sha = "head123"

        mock_compare = Mock()
        mock_compare.merge_base_commit.sha = "merge123"
        mock_repo.compare.return_value = mock_compare

        repository._repository = mock_repo
        repository._pull_request = mock_pr
        repository._initialized = True

        base_sha, head_sha = await repository._get_merge_base_commits()

        assert base_sha == "merge123"
        assert head_sha == "head123"

    async def test_get_merge_base_commits_fallback_on_exception(self, repository):
        """Test fallback to base commit when compare fails."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.base.sha = "base123"
        mock_pr.head.sha = "head123"

        mock_repo.compare.side_effect = GithubException(500, "Error")

        repository._repository = mock_repo
        repository._pull_request = mock_pr
        repository._initialized = True

        base_sha, head_sha = await repository._get_merge_base_commits()

        assert base_sha == "base123"
        assert head_sha == "head123"


class TestGitHubPRDiffRepositoryLogFilteredFiles:
    """Tests for _log_filtered_files method."""

    def test_log_filtered_files_success(self, repository):
        """Test logging filtered files successfully."""
        original_files = [Mock(filename="file1.py"), Mock(filename="file2.py")]
        filtered_files = [Mock(filename="file1.py")]

        # Should not raise exception
        repository._log_filtered_files(original_files, filtered_files)

    def test_log_filtered_files_handles_exception(self, repository):
        """Test that exceptions during logging are handled gracefully."""
        # Create files that will cause exception during attribute access
        original_files = [Mock()]
        del original_files[0].filename  # Remove filename to cause AttributeError
        filtered_files = []

        # Should not raise exception
        repository._log_filtered_files(original_files, filtered_files)


class TestGetGitHubRepository:
    """Tests for get_github_repository factory function."""

    def test_get_github_repository_creates_singleton(self, mock_settings, mock_logger, mock_input_validator):
        """Test that get_github_repository returns same instance for same params."""
        with (
            patch("prdiffer.infrastructure.github_repository.get_github_api_client") as mock_get_client,
            patch("prdiffer.infrastructure.github_repository.get_file_processor"),
            patch("prdiffer.infrastructure.github_repository.get_diff_generator"),
            patch("prdiffer.infrastructure.github_repository.get_pattern_matcher"),
            patch("prdiffer.infrastructure.github_repository.get_diff_utils"),
        ):
            mock_get_client.return_value = Mock()

            repo1 = get_github_repository(
                repo_owner="owner",
                repo_name="repo",
                pr_number=123,
                github_token="token",
                settings_service=mock_settings,
                logger=mock_logger,
                input_validator=mock_input_validator,
            )

            repo2 = get_github_repository(
                repo_owner="owner",
                repo_name="repo",
                pr_number=123,
                github_token="token",
                settings_service=mock_settings,
                logger=mock_logger,
                input_validator=mock_input_validator,
            )

            assert repo1 is repo2

    def test_get_github_repository_different_pr_different_instance(self, mock_settings, mock_logger, mock_input_validator):
        """Test that different PRs return different instances."""
        with (
            patch("prdiffer.infrastructure.github_repository.get_github_api_client") as mock_get_client,
            patch("prdiffer.infrastructure.github_repository.get_file_processor"),
            patch("prdiffer.infrastructure.github_repository.get_diff_generator"),
            patch("prdiffer.infrastructure.github_repository.get_pattern_matcher"),
            patch("prdiffer.infrastructure.github_repository.get_diff_utils"),
        ):
            mock_get_client.return_value = Mock()

            repo1 = get_github_repository(
                repo_owner="owner",
                repo_name="repo",
                pr_number=123,
                settings_service=mock_settings,
                logger=mock_logger,
                input_validator=mock_input_validator,
            )

            repo2 = get_github_repository(
                repo_owner="owner",
                repo_name="repo",
                pr_number=456,
                settings_service=mock_settings,
                logger=mock_logger,
                input_validator=mock_input_validator,
            )

            assert repo1 is not repo2


class TestSanitizeFilenameForLogging:
    """Tests for _sanitize_filename_for_logging method."""

    def test_sanitize_normal_filename(self, repository):
        """Test sanitizing a normal filename."""
        result = repository._sanitize_filename_for_logging("test.py")
        assert "test.py" in result

    def test_sanitize_long_filename(self, repository):
        """Test sanitizing a very long filename."""
        long_name = "a" * 500 + ".py"
        result = repository._sanitize_filename_for_logging(long_name)
        assert len(result) <= 200
