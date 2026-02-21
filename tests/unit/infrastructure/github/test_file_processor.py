"""Unit tests for File Processor.

This module contains comprehensive tests for FileProcessor class,
covering file filtering, thread safety, and batch processing.
"""

import pytest
import anyio
from unittest.mock import Mock

from prdiffer.infrastructure.github.file_processor import FileProcessor
from github.PullRequest import PullRequest
from github.File import File


class TestFileProcessor:
    """Test suite for FileProcessor."""

    @pytest.fixture
    def file_processor(self):
        """Create FileProcessor instance for testing."""
        from prdiffer.infrastructure.utils.pattern_matcher import PatternMatcher
        from prdiffer.infrastructure.github.client import GitHubAPIClient
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils
        from prdiffer.infrastructure.logging.console_logger import get_logger

        mock_api = Mock(spec=GitHubAPIClient)
        mock_matcher = Mock(spec=PatternMatcher)
        mock_diff_utils = Mock(spec=DiffUtils)
        mock_logger = get_logger()

        return FileProcessor(
            github_api_service=mock_api,
            pattern_matcher=mock_matcher,
            diff_utils=mock_diff_utils,
            logger=mock_logger,
        )

    def test_filter_files_with_pattern_matcher(self, file_processor):
        """Test file filtering using pattern matcher."""
        # Create mock files
        mock_file1 = Mock(spec=File)
        mock_file1.filename = 'test.py'
        mock_file2 = Mock(spec=File)
        mock_file2.filename = 'test.lock'
        mock_file3 = Mock(spec=File)
        mock_file3.filename = 'test.js'

        mock_files = [mock_file1, mock_file2, mock_file3]

        # Mock pattern matcher to only accept .py files
        file_processor._pattern_matcher.is_valid_file.side_effect = lambda fname: fname.endswith('.py')

        # Call filter_files (public method)
        filtered = file_processor.filter_files(mock_files)

        # Should only include .py files
        assert len(filtered) == 1
        assert filtered[0].filename == 'test.py'
        # Verify pattern matcher was called for each file
        assert file_processor._pattern_matcher.is_valid_file.call_count == 3


class TestFileProcessorThreadSafety:
    """Test suite for FileProcessor thread safety."""

    @pytest.fixture
    def file_processor(self):
        """Create FileProcessor instance for testing."""
        from prdiffer.infrastructure.utils.pattern_matcher import PatternMatcher
        from prdiffer.infrastructure.github.client import GitHubAPIClient
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils
        from prdiffer.infrastructure.logging.console_logger import get_logger

        mock_api = Mock(spec=GitHubAPIClient)
        mock_matcher = Mock(spec=PatternMatcher)
        mock_diff_utils = Mock(spec=DiffUtils)
        mock_logger = get_logger()

        return FileProcessor(
            github_api_service=mock_api,
            pattern_matcher=mock_matcher,
            diff_utils=mock_diff_utils,
            logger=mock_logger,
        )

    @pytest.mark.asyncio
    async def test_get_pr_files_thread_safety(self, file_processor):
        """Test that get_pr_files is thread-safe with double-check locking."""
        mock_pr = Mock(spec=PullRequest)
        mock_pr.get_files = Mock(return_value=[Mock(spec=File)])

        # Create multiple async tasks that call get_pr_files concurrently
        async with anyio.create_task_group() as tg:
            results = []

            async def get_and_store():
                result = await file_processor.get_pr_files(mock_pr)
                results.append(result)

            for _ in range(10):
                tg.start_soon(get_and_store)

        # All threads should complete without exception
        assert len(results) == 10
        # All should get the same result (from cache after first call)
        for result in results:
            assert result is not None

    @pytest.mark.asyncio
    async def test_cache_consistency_under_concurrent_access(self, file_processor):
        """Test that cache remains consistent under concurrent access."""
        mock_pr = Mock(spec=PullRequest)
        mock_pr.get_files = Mock(return_value=[Mock(spec=File)])

        # Create multiple async tasks accessing cache
        async with anyio.create_task_group() as tg:

            async def call_get_files():
                await file_processor.get_pr_files(mock_pr)

            for _ in range(50):
                tg.start_soon(call_get_files)

        # Cache should be in consistent state
        # get_files should only be called once (first call caches the result)
        assert mock_pr.get_files.call_count == 1


class TestFileProcessorBatchProcessing:
    """Test suite for FileProcessor batch processing."""

    @pytest.fixture
    def file_processor(self):
        """Create FileProcessor instance for testing."""
        from prdiffer.infrastructure.utils.pattern_matcher import PatternMatcher
        from prdiffer.infrastructure.github.client import GitHubAPIClient
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils
        from prdiffer.infrastructure.logging.console_logger import get_logger

        mock_api = Mock(spec=GitHubAPIClient)
        mock_matcher = Mock(spec=PatternMatcher)
        mock_diff_utils = Mock(spec=DiffUtils)
        mock_logger = get_logger()

        return FileProcessor(
            github_api_service=mock_api,
            pattern_matcher=mock_matcher,
            diff_utils=mock_diff_utils,
            logger=mock_logger,
        )

    def test_process_files_to_patches_basic(self, file_processor):
        """Test basic processing of files to FilePatchInfo objects."""
        # Create mock files
        mock_file = Mock(spec=File)
        mock_file.filename = 'test.py'
        mock_file.status = 'modified'
        mock_file.patch = '@@ -1 +1 @@'
        mock_file.additions = 1
        mock_file.deletions = 0

        # Mock the get_files_content_batch method on the internal github_api_service
        # The method returns a dict mapping filename -> decoded content string
        file_processor._github_api_service.get_files_content_batch = Mock(return_value={'test.py': "def hello():\n    print('world')"})

        # Create mock repository
        mock_repo = Mock()

        # Process the file
        result = file_processor.process_files_to_patches([mock_file], mock_repo, 'head_sha', 'base_sha')

        # Should return a list of FilePatchInfo objects
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].filename == 'test.py'
        assert result[0].base_file == "def hello():\n    print('world')"
        assert result[0].head_file == "def hello():\n    print('world')"

    def test_max_files_limit(self, file_processor):
        """Test that max_files_allowed limit is respected."""
        # Test that the limit is set correctly
        assert file_processor.max_files_allowed == 50

        # Create a file processor with smaller limit
        from prdiffer.infrastructure.utils.pattern_matcher import PatternMatcher
        from prdiffer.infrastructure.github.client import GitHubAPIClient
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils
        from prdiffer.infrastructure.logging.console_logger import get_logger

        mock_api = Mock(spec=GitHubAPIClient)
        mock_matcher = Mock(spec=PatternMatcher)
        mock_diff_utils = Mock(spec=DiffUtils)
        mock_logger = get_logger()

        limited_processor = FileProcessor(
            github_api_service=mock_api,
            pattern_matcher=mock_matcher,
            diff_utils=mock_diff_utils,
            max_files_allowed=5,
            logger=mock_logger,
        )

        assert limited_processor.max_files_allowed == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
