"""Comprehensive tests for GitHubPRDiffService."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from github import GithubException

from prdiffer.infrastructure.services.pr_diff_service import (
    GitHubPRDiffService,
    PR_SERVICE_EXCEPTIONS,
)
from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE
from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.pr_diff import PRDiff


@pytest.fixture
def mock_github_api():
    """Create mock GitHub API client."""
    mock = MagicMock()
    mock.initialize_client = MagicMock()
    mock._get_pygithub_repository = MagicMock()
    mock._get_pygithub_pull_request = MagicMock()
    return mock


@pytest.fixture
def mock_file_processor():
    """Create mock file processor."""
    mock = MagicMock()
    mock.process_files_to_patches = MagicMock(return_value=[])
    mock.process_files_to_patches_async = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_diff_generator():
    """Create mock diff generator."""
    mock = MagicMock()
    mock.generate_extended_diff = MagicMock(return_value=[])
    return mock


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return MagicMock()


@pytest.fixture
def sample_file_patch():
    """Create sample FilePatchInfo."""
    return FilePatchInfo(
        filename='src/test.py',
        base_file='old content',
        head_file='new content',
        patch='@@ -1,2 +1,2 @@',
        edit_type=EDIT_TYPE.MODIFIED,
        num_plus_lines=5,
        num_minus_lines=3,
    )


@pytest.fixture
def sample_pr_diff(sample_file_patch):
    """Create sample PRDiff."""
    return PRDiff(
        files=(
            FileDiffResponse(
                path='src/test.py',
                status=EDIT_TYPE.MODIFIED,
                stats=FileStats(additions=5, deletions=3),
                diff='test diff',
            ),
        )
    )


class TestGitHubPRDiffServiceInit:
    """Tests for GitHubPRDiffService initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch.dict('os.environ', {'GITHUB_TOKEN': '', 'GITHUB_TIMEOUT': '30'}):
            service = GitHubPRDiffService()

            assert service._github_api is not None
            assert service._diff_generator is None
            assert service._file_processor is None

    def test_init_with_custom_components(self, mock_github_api, mock_diff_generator, mock_file_processor, mock_logger):
        """Test initialization with custom components."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            diff_generator=mock_diff_generator,
            file_processor=mock_file_processor,
            logger=mock_logger,
        )

        assert service._github_api is mock_github_api
        assert service._diff_generator is mock_diff_generator
        assert service._file_processor is mock_file_processor
        assert service._logger is mock_logger

    def test_init_caching_mixin(self, mock_github_api):
        """Test that caching mixin is initialized."""
        service = GitHubPRDiffService(github_api_client=mock_github_api)

        assert hasattr(service, '_method_cache')
        assert hasattr(service, '_cache_lock')


class TestGetPrDiff:
    """Tests for get_pr_diff method."""

    @pytest.mark.anyio
    async def test_get_pr_diff_async_path(self, mock_github_api, mock_file_processor, mock_logger):
        """Test async path when file processor has async method."""
        mock_file_processor.process_files_to_patches_async = AsyncMock(
            return_value=[
                FilePatchInfo(
                    filename='test.py',
                    base_file='',
                    head_file='',
                    patch='patch',
                    edit_type=EDIT_TYPE.MODIFIED,
                    num_plus_lines=1,
                    num_minus_lines=1,
                )
            ]
        )

        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.head.sha = 'abc123'
        mock_pr.base.sha = 'def456'
        mock_pr.get_files.return_value = []

        mock_github_api._get_pygithub_repository.return_value = mock_repo
        mock_github_api._get_pygithub_pull_request.return_value = mock_pr

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            file_processor=mock_file_processor,
            logger=mock_logger,
        )

        result = await service.get_pr_diff('owner', 'repo', 1)

        assert result is not None

    @pytest.mark.anyio
    async def test_get_pr_diff_sync_fallback(self, mock_github_api, mock_logger):
        """Test sync fallback when no file processor."""
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.head.sha = 'abc123'
        mock_pr.base.sha = 'def456'
        mock_pr.get_files.return_value = []

        mock_github_api._get_pygithub_repository.return_value = mock_repo
        mock_github_api._get_pygithub_pull_request.return_value = mock_pr

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            file_processor=None,
            logger=mock_logger,
        )

        result = await service.get_pr_diff('owner', 'repo', 1)

        assert result is not None

    @pytest.mark.anyio
    async def test_get_pr_diff_repository_not_found(self, mock_github_api, mock_logger):
        """Test when repository not found."""
        mock_github_api._get_pygithub_repository.return_value = None

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = await service.get_pr_diff('owner', 'repo', 1)

        assert result is None

    @pytest.mark.anyio
    async def test_get_pr_diff_pr_not_found(self, mock_github_api, mock_logger):
        """Test when PR not found."""
        mock_repo = MagicMock()
        mock_github_api._get_pygithub_repository.return_value = mock_repo
        mock_github_api._get_pygithub_pull_request.return_value = None

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = await service.get_pr_diff('owner', 'repo', 1)

        assert result is None

    @pytest.mark.anyio
    async def test_get_pr_diff_exception_handling(self, mock_github_api, mock_logger):
        """Test exception handling in get_pr_diff."""
        mock_github_api._get_pygithub_repository.side_effect = GithubException(500, 'Error', {})

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = await service.get_pr_diff('owner', 'repo', 1)

        assert result is None


class TestGetPrDiffSync:
    """Tests for _get_pr_diff_sync method."""

    def test_get_pr_diff_sync_success(self, mock_github_api, mock_logger, sample_file_patch):
        """Test successful sync diff retrieval."""
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.head.sha = 'abc123'
        mock_pr.base.sha = 'def456'
        mock_pr.get_files.return_value = []

        mock_github_api._get_pygithub_repository.return_value = mock_repo
        mock_github_api._get_pygithub_pull_request.return_value = mock_pr

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        with patch.object(service, '_generate_diff_content', return_value=[sample_file_patch]):
            result = service._get_pr_diff_sync('owner', 'repo', 1)

            assert result is not None
            assert isinstance(result, PRDiff)

    def test_get_pr_diff_sync_repository_none(self, mock_github_api, mock_logger):
        """Test sync when repository is None."""
        mock_github_api._get_pygithub_repository.return_value = None

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service._get_pr_diff_sync('owner', 'repo', 1)

        assert result is None

    def test_get_pr_diff_sync_pr_none(self, mock_github_api, mock_logger):
        """Test sync when PR is None."""
        mock_repo = MagicMock()
        mock_github_api._get_pygithub_repository.return_value = mock_repo
        mock_github_api._get_pygithub_pull_request.return_value = None

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service._get_pr_diff_sync('owner', 'repo', 1)

        assert result is None

    def test_get_pr_diff_sync_exception(self, mock_github_api, mock_logger):
        """Test sync with exception."""
        mock_github_api._get_pygithub_repository.side_effect = RuntimeError('Error')

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service._get_pr_diff_sync('owner', 'repo', 1)

        assert result is None


class TestGetLatestCommitSha:
    """Tests for get_latest_commit_sha method."""

    @pytest.mark.anyio
    async def test_get_latest_commit_sha_success(self, mock_github_api, mock_logger):
        """Test successful commit SHA retrieval."""
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.head.sha = 'abc123'

        mock_github_api._get_pygithub_repository.return_value = mock_repo
        mock_github_api._get_pygithub_pull_request.return_value = mock_pr

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = await service.get_latest_commit_sha('owner', 'repo', 1)

        assert result == 'abc123'

    @pytest.mark.anyio
    async def test_get_latest_commit_sha_repository_none(self, mock_github_api, mock_logger):
        """Test when repository is None."""
        mock_github_api._get_pygithub_repository.return_value = None

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = await service.get_latest_commit_sha('owner', 'repo', 1)

        assert result is None

    @pytest.mark.anyio
    async def test_get_latest_commit_sha_pr_none(self, mock_github_api, mock_logger):
        """Test when PR is None."""
        mock_repo = MagicMock()
        mock_github_api._get_pygithub_repository.return_value = mock_repo
        mock_github_api._get_pygithub_pull_request.return_value = None

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = await service.get_latest_commit_sha('owner', 'repo', 1)

        assert result is None


class TestConvertGithubFilesToFilePatchInfo:
    """Tests for _convert_github_files_to_file_patch_info method."""

    def test_convert_modified_file(self, mock_github_api, mock_logger):
        """Test converting modified file."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        mock_file = MagicMock()
        mock_file.filename = 'test.py'
        mock_file.status = 'modified'
        mock_file.patch = '@@ -1,2 +1,2 @@'
        mock_file.additions = 5
        mock_file.deletions = 3

        result = service._convert_github_files_to_file_patch_info([mock_file])

        assert len(result) == 1
        assert result[0].filename == 'test.py'
        assert result[0].edit_type == EDIT_TYPE.MODIFIED

    def test_convert_added_file(self, mock_github_api, mock_logger):
        """Test converting added file."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        mock_file = MagicMock()
        mock_file.filename = 'new.py'
        mock_file.status = 'added'
        mock_file.patch = '@@ -0,0 +1,5 @@'
        mock_file.additions = 5
        mock_file.deletions = 0

        result = service._convert_github_files_to_file_patch_info([mock_file])

        assert result[0].edit_type == EDIT_TYPE.ADDED

    def test_convert_removed_file(self, mock_github_api, mock_logger):
        """Test converting removed file."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        mock_file = MagicMock()
        mock_file.filename = 'deleted.py'
        mock_file.status = 'removed'
        mock_file.patch = '@@ -1,5 +0,0 @@'
        mock_file.additions = 0
        mock_file.deletions = 5

        result = service._convert_github_files_to_file_patch_info([mock_file])

        assert result[0].edit_type == EDIT_TYPE.DELETED

    def test_convert_renamed_file(self, mock_github_api, mock_logger):
        """Test converting renamed file."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        mock_file = MagicMock()
        mock_file.filename = 'renamed.py'
        mock_file.status = 'renamed'
        mock_file.patch = ''
        mock_file.additions = 0
        mock_file.deletions = 0

        result = service._convert_github_files_to_file_patch_info([mock_file])

        assert result[0].edit_type == EDIT_TYPE.RENAMED

    def test_convert_unknown_status(self, mock_github_api, mock_logger):
        """Test converting file with unknown status."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        mock_file = MagicMock()
        mock_file.filename = 'unknown.py'
        mock_file.status = 'changed'
        mock_file.patch = ''
        mock_file.additions = 0
        mock_file.deletions = 0

        result = service._convert_github_files_to_file_patch_info([mock_file])

        assert result[0].edit_type == EDIT_TYPE.UNKNOWN


class TestMapGithubStatusToEditType:
    """Tests for _map_github_status_to_edit_type method."""

    def test_map_added(self, mock_github_api, mock_logger):
        """Test mapping added status."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        assert service._map_github_status_to_edit_type('added') == EDIT_TYPE.ADDED

    def test_map_removed(self, mock_github_api, mock_logger):
        """Test mapping removed status."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        assert service._map_github_status_to_edit_type('removed') == EDIT_TYPE.DELETED

    def test_map_modified(self, mock_github_api, mock_logger):
        """Test mapping modified status."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        assert service._map_github_status_to_edit_type('modified') == EDIT_TYPE.MODIFIED

    def test_map_renamed(self, mock_github_api, mock_logger):
        """Test mapping renamed status."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        assert service._map_github_status_to_edit_type('renamed') == EDIT_TYPE.RENAMED

    def test_map_unknown(self, mock_github_api, mock_logger):
        """Test mapping unknown status."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        assert service._map_github_status_to_edit_type('other') == EDIT_TYPE.UNKNOWN


class TestConvertFilePatchInfoToResponse:
    """Tests for _convert_file_patch_info_to_response method."""

    def test_convert_file_patch(self, mock_github_api, mock_logger, sample_file_patch):
        """Test converting FilePatchInfo to response."""
        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service._convert_file_patch_info_to_response(sample_file_patch)

        assert isinstance(result, FileDiffResponse)
        assert result.path == 'src/test.py'
        assert result.status == EDIT_TYPE.MODIFIED
        assert result.stats.additions == 5
        assert result.stats.deletions == 3


class TestGenerateDiffContent:
    """Tests for _generate_diff_content method."""

    def test_generate_diff_with_file_processor(self, mock_github_api, mock_file_processor, mock_logger):
        """Test diff generation with file processor."""
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.head.sha = 'abc123'
        mock_pr.base.sha = 'def456'

        mock_file = MagicMock()
        mock_file.filename = 'test.py'
        mock_pr.get_files.return_value = [mock_file]

        mock_file_processor.process_files_to_patches.return_value = [
            FilePatchInfo(
                filename='test.py',
                base_file='',
                head_file='',
                patch='patch',
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=1,
                num_minus_lines=1,
            )
        ]

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            file_processor=mock_file_processor,
            logger=mock_logger,
        )

        result = service._generate_diff_content(mock_repo, mock_pr)

        assert len(result) == 1

    def test_generate_diff_without_file_processor(self, mock_github_api, mock_logger):
        """Test diff generation without file processor."""
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.head.sha = 'abc123'
        mock_pr.base.sha = 'def456'

        mock_file = MagicMock()
        mock_file.filename = 'test.py'
        mock_file.status = 'modified'
        mock_file.patch = 'patch'
        mock_file.additions = 1
        mock_file.deletions = 1
        mock_pr.get_files.return_value = [mock_file]

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            file_processor=None,
            logger=mock_logger,
        )

        result = service._generate_diff_content(mock_repo, mock_pr)

        assert len(result) == 1

    def test_generate_diff_no_commit_sha(self, mock_github_api, mock_logger):
        """Test diff generation with no commit SHA."""
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.head.sha = None

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service._generate_diff_content(mock_repo, mock_pr)

        assert result == []

    def test_generate_diff_no_files(self, mock_github_api, mock_logger):
        """Test diff generation with no files."""
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.head.sha = 'abc123'
        mock_pr.base.sha = 'def456'
        mock_pr.get_files.return_value = None

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service._generate_diff_content(mock_repo, mock_pr)

        assert result == []


class TestGetBaseCommitSha:
    """Tests for _get_base_commit_sha method."""

    def test_get_base_commit_sha_from_base(self, mock_github_api, mock_logger):
        """Test getting base SHA from base attribute."""
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.base.sha = 'basesha'

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service._get_base_commit_sha(mock_repo, mock_pr)

        assert result == 'basesha'

    def test_get_base_commit_sha_from_ref(self, mock_github_api, mock_logger):
        """Test getting base SHA from ref."""
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.base.sha = None
        mock_pr.base.ref = 'main'

        mock_ref = MagicMock()
        mock_ref.object.sha = 'refsha'
        mock_repo.get_git_ref.return_value = mock_ref

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service._get_base_commit_sha(mock_repo, mock_pr)

        assert result == 'refsha'

    def test_get_base_commit_sha_none(self, mock_github_api, mock_logger):
        """Test getting base SHA when not available."""
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.base.sha = None
        mock_pr.base.ref = 'main'
        mock_repo.get_git_ref.return_value = None

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service._get_base_commit_sha(mock_repo, mock_pr)

        assert result is None


class TestValidateRepositoryAccess:
    """Tests for validate_repository_access method."""

    def test_validate_repository_access_success(self, mock_github_api, mock_logger):
        """Test successful repository access validation."""
        mock_github_api.get_repository.return_value = MagicMock()

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service.validate_repository_access('owner', 'repo')

        assert result is True

    def test_validate_repository_access_not_found(self, mock_github_api, mock_logger):
        """Test repository not found."""
        mock_github_api.get_repository.return_value = None

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service.validate_repository_access('owner', 'repo')

        assert result is False

    def test_validate_repository_access_exception(self, mock_github_api, mock_logger):
        """Test exception during validation."""
        mock_github_api.get_repository.side_effect = GithubException(500, 'Error', {})

        service = GitHubPRDiffService(
            github_api_client=mock_github_api,
            logger=mock_logger,
        )

        result = service.validate_repository_access('owner', 'repo')

        assert result is False


class TestPRServiceExceptions:
    """Tests for PR_SERVICE_EXCEPTIONS tuple."""

    def test_exceptions_tuple(self):
        """Test that expected exceptions are in the tuple."""
        assert GithubException in PR_SERVICE_EXCEPTIONS
        assert TimeoutError in PR_SERVICE_EXCEPTIONS
        assert ConnectionError in PR_SERVICE_EXCEPTIONS
        assert OSError in PR_SERVICE_EXCEPTIONS
        assert RuntimeError in PR_SERVICE_EXCEPTIONS
        assert ValueError in PR_SERVICE_EXCEPTIONS
        assert TypeError in PR_SERVICE_EXCEPTIONS
