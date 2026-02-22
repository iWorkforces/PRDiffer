"""Unit tests for pr_diff_service returning FilePatchInfo list.

Tests that PRDiffService returns List[FilePatchInfo] instead of concatenated string.
Breaking change for structured file-level output.

WAVE 1 & 2 COMPLETE: Domain entities updated with new structure
"""

import pytest
from unittest.mock import Mock, AsyncMock

from prdiffer.infrastructure.services.pr_diff_service import GitHubPRDiffService
from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE


@pytest.mark.asyncio
class TestGenerateDiffContentReturnsFilePatchList:
    """Test that _generate_diff_content returns FilePatchInfo list."""

    async def test_generate_diff_content_returns_file_patch_list(self):
        """Test _generate_diff_content returns List[FilePatchInfo] not concatenated string."""
        # Arrange
        mock_github_api_client = Mock()
        mock_file_processor = Mock()
        mock_diff_generator = Mock()

        # Setup mock to return FilePatchInfo list
        mock_github_api_client = Mock()
        mock_file_processor = Mock()
        mock_diff_generator = Mock()

        # Create FilePatchInfo objects (domain entity from domain layer)
        file_patch_1 = FilePatchInfo(
            filename="file1.ts",
            edit_type=EDIT_TYPE.ADDED,
            num_plus_lines=100,
            num_minus_lines=0,
            patch="@@ -0,0 +1,100 @@\n+new\n",
        )

        file_patch_2 = FilePatchInfo(
            filename="file2.ts",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=50,
            num_minus_lines=25,
            patch="@@ -1,3 +1,8 @@\n-old\n+new\n",
        )

        # Setup mock to return FilePatchInfo list (both sync and async methods)
        mock_file_processor.process_files_to_patches.return_value = [
            file_patch_1,
            file_patch_2,
        ]
        mock_file_processor.process_files_to_patches_async = AsyncMock(return_value=[file_patch_1, file_patch_2])

        # Setup diff generator to return list of strings
        mock_diff_generator.generate_extended_diff.return_value = [
            "diff content for file1",
            "diff content for file2",
        ]

        service = GitHubPRDiffService(
            github_api_client=mock_github_api_client,
            file_processor=mock_file_processor,
            diff_generator=mock_diff_generator,
        )

        # Create mock repository and PR
        mock_repository = Mock()
        mock_pull_request = Mock()
        mock_pull_request.head = Mock()
        mock_pull_request.head.sha = "commit123"
        mock_pull_request.get_files.return_value = [Mock(), Mock()]  # 2 mock files
        mock_pull_request.base = Mock()
        mock_pull_request.base.sha = "base123"

        mock_github_api_client.get_repository.return_value = mock_repository
        mock_github_api_client.get_pull_request.return_value = mock_pull_request

        # Act
        result = await service._generate_diff_content_async(mock_repository, mock_pull_request)

        # Assert - expecting tuple[str, list[FilePatchInfo]] after breaking change
        assert isinstance(result, tuple)
        diff_content, diff_files = result
        assert isinstance(diff_files, list)
        assert len(diff_files) == 2
        assert all(isinstance(f, FilePatchInfo) for f in diff_files)
        assert diff_files[0].filename == "file1.ts"
        assert diff_files[1].filename == "file2.ts"
