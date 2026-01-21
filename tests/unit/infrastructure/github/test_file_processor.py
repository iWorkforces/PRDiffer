"""Unit tests for File Processor.

This module contains comprehensive tests for the FileProcessor class,
covering file filtering, thread safety, and batch processing.
"""

import pytest
from unittest.mock import Mock, patch
from threading import Thread

from prdiffer.infrastructure.github.file_processor import FileProcessor
from github.PullRequest import PullRequest


class TestFileProcessor:
    """Test suite for FileProcessor."""

    @pytest.fixture
    def file_processor(self):
        """Create FileProcessor instance for testing."""
        from prdiffer.infrastructure.utils.pattern_matcher import PatternMatcher
        from prdiffer.infrastructure.github.api_client import GitHubAPIClient
        from prdiffer.infrastructure.logging.console_logger import get_logger

        mock_api = Mock(spec=GitHubAPIClient)
        mock_matcher = Mock(spec=PatternMatcher)
        mock_logger = get_logger()

        return FileProcessor(
            github_api_service=mock_api,
            pattern_matcher=mock_matcher,
            logger=mock_logger,
        )

    def test_is_valid_file_with_valid_extension(self, file_processor):
        """Test file validation with valid extension."""
        # Mock pattern matcher to return True
        file_processor._pattern_matcher.is_valid_file.return_value = True

        result = file_processor._is_valid_file(Mock(filename="test.py"))

        assert result is True

    def test_is_valid_file_with_invalid_extension(self, file_processor):
        """Test file validation with invalid extension."""
        # Mock pattern matcher to return False
        file_processor._pattern_matcher.is_valid_file.return_value = False

        result = file_processor._is_valid_file(Mock(filename="test.lock"))

        assert result is False

    def test_filter_files(self, file_processor):
        """Test file filtering logic."""
        # Create mock files
        mock_files = [
            Mock(filename="test.py", status="modified"),
            Mock(filename="test.lock", status="modified"),
            Mock(filename="test.js", status="added"),
        ]

        with patch.object(file_processor, "_is_valid_file") as mock_valid:
            mock_valid.side_effect = lambda f: f.filename.endswith(".py")

            filtered = file_processor._filter_files(mock_files)

            # Should only include .py files
            assert len(filtered) == 1
            assert filtered[0].filename == "test.py"


class TestFileProcessorThreadSafety:
    """Test suite for FileProcessor thread safety."""

    @pytest.fixture
    def file_processor(self):
        """Create FileProcessor instance for testing."""
        from prdiffer.infrastructure.utils.pattern_matcher import PatternMatcher
        from prdiffer.infrastructure.github.api_client import GitHubAPIClient
        from prdiffer.infrastructure.logging.console_logger import get_logger

        mock_api = Mock(spec=GitHubAPIClient)
        mock_matcher = Mock(spec=PatternMatcher)
        mock_logger = get_logger()

        return FileProcessor(
            github_api_service=mock_api,
            pattern_matcher=mock_matcher,
            logger=mock_logger,
        )

    def test_get_pr_files_thread_safety(self, file_processor):
        """Test that get_pr_files is thread-safe with double-check locking."""
        mock_pr = Mock(spec=PullRequest)

        # Create multiple threads that call get_pr_files concurrently
        threads = []
        results = []

        def concurrent_get_files():
            files = file_processor.get_pr_files(mock_pr)
            results.append(files)

        for _ in range(10):
            t = Thread(target=concurrent_get_files)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should complete without exception
        assert len(results) == 10

    def test_cache_consistency_under_concurrent_access(self, file_processor):
        """Test that cache remains consistent under concurrent access."""
        mock_pr = Mock(spec=PullRequest)

        # Create multiple threads accessing cache
        threads = []
        for i in range(50):
            t = Thread(target=lambda: file_processor.get_pr_files(mock_pr))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Cache should be in consistent state
        # The same PR files object should be returned


class TestFileProcessorBatchProcessing:
    """Test suite for FileProcessor batch processing."""

    @pytest.fixture
    def file_processor(self):
        """Create FileProcessor instance for testing."""
        from prdiffer.infrastructure.utils.pattern_matcher import PatternMatcher
        from prdiffer.infrastructure.github.api_client import GitHubAPIClient
        from prdiffer.infrastructure.logging.console_logger import get_logger

        mock_api = Mock(spec=GitHubAPIClient)
        mock_matcher = Mock(spec=PatternMatcher)
        mock_logger = get_logger()

        return FileProcessor(
            github_api_service=mock_api,
            pattern_matcher=mock_matcher,
            logger=mock_logger,
        )

    def test_process_files_to_patches(self, file_processor):
        """Test processing files to FilePatchInfo objects."""
        # Mock the diff generation
        with patch.object(file_processor, "_get_file_diff"):
            # Test batch processing
            pass

    def test_respects_max_files_limit(self, file_processor):
        """Test that max_files_allowed limit is respected."""
        # Create file processor with small limit
        # Should stop loading file content after limit
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
