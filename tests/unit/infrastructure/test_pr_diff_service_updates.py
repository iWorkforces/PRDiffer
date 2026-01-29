"""Unit tests for pr_diff_service returning FilePatchInfo list.

Tests that PRDiffService returns List[FilePatchInfo] instead of concatenated string.
Breaking change for structured file-level output.

WAVE 1 & 2 COMPLETE: Domain entities updated with new structure
"""

import pytest
from unittest.mock import Mock

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

        # Setup mock to return FilePatchInfo list
        mock_file_processor.process_files_to_patches.return_value = [
            file_patch_1,
            file_patch_2,
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
        mock_pull_request.get_files.return_value = []
        mock_pull_request.base = None

        mock_github_api_client.get_repository.return_value = mock_repository
        mock_github_api_client.get_pull_request.return_value = mock_pull_request

        # Act
        result = await service._generate_diff_content_async(
            mock_repository, mock_pull_request
        )

        # Assert - expecting List[FilePatchInfo] after breaking change
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(f, FilePatchInfo) for f in result)
        assert result[0].filename == "file1.ts"
        assert result[1].filename == "file2.ts"
