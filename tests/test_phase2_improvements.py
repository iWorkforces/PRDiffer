"""
Tests for Phase 2 Improvements: Diff Builder Optimization

This module contains unit tests for Phase 2 improvements including:
- Binary file handling
- Chunked processing for large files
- Streaming diff generation
- Parallel batch fetching
- Line numbering edge cases
"""

import pytest
from unittest.mock import Mock, patch

# =============================================================================
# Phase 2.1: Binary File Handling Tests (diff_utils.py)
# =============================================================================


class TestBinaryFileHandling:
    """Tests for binary file pre-check in diff_utils.py"""

    def test_binary_content_detection_null_bytes(self):
        """Test that content with null bytes is detected as binary."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        # Content with null bytes should be detected as binary
        binary_content = "Hello\x00World"
        assert diff_utils._is_binary_content(binary_content) is True

    def test_binary_content_detection_high_non_printable_ratio(self):
        """Test that content with high ratio of non-printable chars is binary."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        # Create content with more than 30% non-printable characters
        non_printable = chr(1) * 50  # Non-printable control chars
        printable = "a" * 100
        binary_content = non_printable + printable

        assert diff_utils._is_binary_content(binary_content) is True

    def test_binary_content_detection_normal_text(self):
        """Test that normal text content is not detected as binary."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        # Normal text with tabs and newlines should NOT be binary
        normal_content = "Hello\nWorld\tThis is normal text\n"
        assert diff_utils._is_binary_content(normal_content) is False

    def test_binary_content_detection_empty(self):
        """Test that empty content is not detected as binary."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()
        assert diff_utils._is_binary_content("") is False

    def test_extend_patch_skips_binary_files(self):
        """Test that extend_patch returns binary marker for binary content."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        # Binary content should return binary marker
        binary_original = "Hello\x00World"
        binary_new = "New\x00Content"
        patch = "@@ diff"

        result = diff_utils.extend_patch(binary_original, patch, binary_new)
        assert result == "[BINARY FILE - DIFF NOT AVAILABLE]"

    def test_extend_patch_processes_text_files(self):
        """Test that extend_patch processes normal text files."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        original = "line1\nline2"
        new = "line1\nline2\nline3"
        patch = "@@ -1,2 +1,3 @@"

        result = diff_utils.extend_patch(original, patch, new)
        assert result != "[BINARY FILE - DIFF NOT AVAILABLE]"
        assert "@@ -" in result


# =============================================================================
# Phase 2.2: Chunked Processing Tests (diff_utils.py)
# =============================================================================


class TestChunkedProcessing:
    """Tests for chunked processing of large files."""

    def test_is_large_file_below_threshold(self):
        """Test files below threshold are not considered large."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        small_content = "line\n" * 100  # 100 lines
        assert diff_utils.is_large_file(small_content, threshold=5000) is False

    def test_is_large_file_above_threshold(self):
        """Test files above threshold are considered large."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        large_content = "line\n" * 6000  # 6000 lines
        assert diff_utils.is_large_file(large_content, threshold=5000) is True

    def test_get_file_line_count(self):
        """Test line count calculation."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        assert diff_utils.get_file_line_count("") == 0
        assert diff_utils.get_file_line_count("single line") == 1
        assert diff_utils.get_file_line_count("line1\nline2\nline3") == 3

    def test_build_chunk_hunk_with_changes(self):
        """Test chunk hunk generation with actual changes."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        orig_lines = ["line1", "line2", "line3"]
        new_lines = ["line1", "modified", "line3"]

        result = diff_utils._build_chunk_hunk(orig_lines, new_lines, 1, 1)

        assert "@@ -1,3 +1,3 @@" in result
        assert "-line2" in result
        assert "+modified" in result

    def test_build_chunk_hunk_no_changes(self):
        """Test chunk hunk generation with no changes."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        orig_lines = ["line1", "line2"]
        new_lines = ["line1", "line2"]  # Same content

        result = diff_utils._build_chunk_hunk(orig_lines, new_lines, 1, 1)

        # No changes should return empty string
        assert result == ""

    def test_build_full_file_patch_chunked_small_file(self):
        """Test chunked processing falls back to standard for small files."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        original = "line1\nline2"
        new = "line1\nmodified"

        result = diff_utils.build_full_file_patch_chunked(
            original, new, chunk_size=1000, large_file_threshold=5000
        )

        # Should return a valid diff
        assert "@@ -" in result

    def test_build_full_file_patch_chunked_large_file(self):
        """Test chunked processing for large files."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        # Create large files (just above threshold)
        original = "\n".join([f"original_line_{i}" for i in range(100)])
        new = "\n".join([f"new_line_{i}" for i in range(100)])

        result = diff_utils.build_full_file_patch_chunked(
            original, new, chunk_size=50, large_file_threshold=50
        )

        # Should return a valid diff with multiple hunks
        assert result != ""
        assert "@@ -" in result


# =============================================================================
# Phase 2.3: Streaming Diff Generation Tests (diff_generator.py)
# =============================================================================


class TestStreamingDiffGeneration:
    """Tests for streaming diff generation support."""

    @pytest.fixture
    def mock_diff_utils(self):
        """Create mock diff utils service."""
        mock = Mock()
        mock.extend_patch.return_value = "@@ -1,3 +1,3 @@\n-old\n+new"
        return mock

    @pytest.fixture
    def diff_generator(self, mock_diff_utils):
        """Create DiffGenerator with mocked dependencies."""
        from prdiffer.infrastructure.github.diff_generator import DiffGenerator

        return DiffGenerator(diff_utils=mock_diff_utils)

    @pytest.fixture
    def sample_file_patches(self):
        """Create sample FilePatchInfo objects."""
        from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        return [
            FilePatchInfo(
                base_file="old content 1",
                head_file="new content 1",
                patch="@@ -1 +1 @@\n-old\n+new",
                filename="file1.py",
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=1,
                num_minus_lines=1,
            ),
            FilePatchInfo(
                base_file="old content 2",
                head_file="new content 2",
                patch="@@ -1 +1 @@\n-old2\n+new2",
                filename="file2.py",
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=1,
                num_minus_lines=1,
            ),
        ]

    @pytest.mark.asyncio
    async def test_generate_extended_diff_stream_yields_results(
        self, diff_generator, sample_file_patches
    ):
        """Test that streaming generator yields diff strings."""
        results = []
        async for diff in diff_generator.generate_extended_diff_stream(
            sample_file_patches
        ):
            results.append(diff)

        assert len(results) == 2
        assert all(isinstance(r, str) for r in results)

    @pytest.mark.asyncio
    async def test_generate_extended_diff_stream_progress_callback(
        self, diff_generator, sample_file_patches
    ):
        """Test that progress callback is called."""
        progress_calls = []

        def on_progress(done, total):
            progress_calls.append((done, total))

        async for _ in diff_generator.generate_extended_diff_stream(
            sample_file_patches, batch_size=1, on_progress=on_progress
        ):
            pass

        # Progress should be called at batch boundaries
        assert len(progress_calls) >= 1

    @pytest.mark.asyncio
    async def test_generate_extended_diff_stream_skips_empty_patches(
        self, diff_generator
    ):
        """Test that files without patches are skipped."""
        from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        files = [
            FilePatchInfo(
                base_file="",
                head_file="new",
                patch="",  # Empty patch
                filename="empty.py",
                edit_type=EDIT_TYPE.ADDED,
                num_plus_lines=0,
                num_minus_lines=0,
            ),
        ]

        results = []
        async for diff in diff_generator.generate_extended_diff_stream(files):
            results.append(diff)

        # Empty patches should be skipped
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_generate_single_diff_success(self, diff_generator):
        """Test single diff generation."""
        from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        file = FilePatchInfo(
            base_file="old",
            head_file="new",
            patch="@@ -1 +1 @@\n-old\n+new",
            filename="test.py",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=1,
            num_minus_lines=1,
        )

        result = await diff_generator.generate_single_diff(file)

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_generate_single_diff_empty_patch(self, diff_generator):
        """Test single diff generation with empty patch."""
        from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        file = FilePatchInfo(
            base_file="",
            head_file="new",
            patch="",
            filename="test.py",
            edit_type=EDIT_TYPE.ADDED,
            num_plus_lines=0,
            num_minus_lines=0,
        )

        result = await diff_generator.generate_single_diff(file)

        assert result is None


# =============================================================================
# Phase 2.4: Parallel Batch Fetching Tests (api_client.py)
# =============================================================================


class TestParallelBatchFetching:
    """Tests for parallel batch file fetching."""

    @pytest.fixture
    def api_client(self):
        """Create GitHub API client for testing."""
        from prdiffer.infrastructure.github.api_client import GitHubAPIClient

        client = GitHubAPIClient(
            max_retries=1,
            retry_delay=0.1,
            file_content_cache_max_size=100,
            file_content_cache_ttl=60,
        )
        return client

    def test_parallel_batch_fetch_uses_cache(self, api_client):
        """Test that parallel batch fetch uses cache for already cached files."""
        # Pre-populate cache
        api_client._cache_set(("file1.py", "branch"), "cached content 1")
        api_client._cache_set(("file2.py", "branch"), "cached content 2")

        mock_repo = Mock()

        results = api_client.get_files_content_batch_parallel(
            mock_repo, ["file1.py", "file2.py"], "branch"
        )

        # Should get from cache without API calls
        assert results["file1.py"] == "cached content 1"
        assert results["file2.py"] == "cached content 2"

    def test_parallel_batch_fetch_fetches_uncached(self, api_client):
        """Test that parallel batch fetch fetches uncached files."""
        mock_repo = Mock()
        mock_content = Mock()
        mock_content.decoded_content = b"file content"
        mock_repo.get_contents.return_value = mock_content

        # Initialize the client
        api_client._github_client = Mock()

        with patch.object(
            api_client._retry_handler,
            "execute_with_retry",
            return_value=mock_content,
        ):
            results = api_client.get_files_content_batch_parallel(
                mock_repo, ["file1.py"], "branch"
            )

            assert "file1.py" in results

    def test_parallel_batch_fetch_handles_errors(self, api_client):
        """Test that parallel batch fetch handles errors gracefully."""
        mock_repo = Mock()

        with patch.object(
            api_client,
            "get_file_content",
            side_effect=Exception("API Error"),
        ):
            results = api_client.get_files_content_batch_parallel(
                mock_repo, ["file1.py"], "branch"
            )

            # Should return empty string on error
            assert results["file1.py"] == ""


class TestFileProcessorParallelContent:
    """Tests for parallel content processing in file_processor.py"""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for file processor."""
        github_api = Mock()
        pattern_matcher = Mock()
        pattern_matcher.is_valid_file.return_value = True
        diff_utils = Mock()

        return github_api, pattern_matcher, diff_utils

    @pytest.fixture
    def file_processor(self, mock_services):
        """Create FileProcessor with mocked dependencies."""
        from prdiffer.infrastructure.github.file_processor import FileProcessor

        github_api, pattern_matcher, diff_utils = mock_services

        return FileProcessor(
            github_api_service=github_api,
            pattern_matcher=pattern_matcher,
            diff_utils=diff_utils,
            max_files_allowed=50,
        )

    @pytest.mark.skip(
        reason="Tests deprecated _process_files_with_content_parallel() method. "
        "Internal implementation changed to async (_process_files_with_content_parallel_async). "
        "Tests would need to be rewritten to test the new async implementation."
    )
    def test_parallel_content_processing_separates_by_status(
        self, file_processor, mock_services
    ):
        """Test that parallel processing correctly separates files by status."""
        github_api, _, _ = mock_services

        # Mock the batch methods
        github_api.get_files_content_batch = Mock(return_value={})
        github_api.get_files_content_batch_parallel = Mock(return_value={})

        # Create mock files (only added and modified - removed files are skipped)
        mock_files = []
        for status in ["added", "modified"]:
            mock_file = Mock()
            mock_file.filename = f"{status}_file.py"
            mock_file.status = status
            mock_file.patch = "@@ -1 +1 @@"
            mock_file.additions = 1
            mock_file.deletions = 1
            mock_files.append(mock_file)

        mock_repo = Mock()

        # Call parallel processing
        result = file_processor._process_files_with_content_parallel(
            mock_files, mock_repo, "head_sha", "base_sha"
        )

        # Should return FilePatchInfo objects for non-deleted files
        assert len(result) == 2

    @pytest.mark.skip(
        reason="Tests deprecated _process_files_with_content_parallel() method. "
        "Internal implementation changed to async (_process_files_with_content_parallel_async). "
        "Tests would need to be rewritten to test the new async implementation."
    )
    def test_parallel_content_processing_skips_deleted_files(
        self, file_processor, mock_services
    ):
        """Test that deleted files are skipped from diff output."""
        github_api, _, _ = mock_services

        # Mock the batch methods
        github_api.get_files_content_batch = Mock(return_value={})
        github_api.get_files_content_batch_parallel = Mock(return_value={})

        # Create mock files including a deleted file
        mock_files = []
        for status in ["added", "modified", "removed"]:
            mock_file = Mock()
            mock_file.filename = f"{status}_file.py"
            mock_file.status = status
            mock_file.patch = "@@ -1 +1 @@"
            mock_file.additions = 1 if status != "removed" else 0
            mock_file.deletions = 1 if status != "removed" else 5
            mock_files.append(mock_file)

        mock_repo = Mock()

        # Call parallel processing
        result = file_processor._process_files_with_content_parallel(
            mock_files, mock_repo, "head_sha", "base_sha"
        )

        # Should return only 2 FilePatchInfo objects (deleted file skipped)
        assert len(result) == 2

        # Verify that the result only contains added and modified files
        filenames = [f.filename for f in result]
        assert "added_file.py" in filenames
        assert "modified_file.py" in filenames
        assert "removed_file.py" not in filenames


# =============================================================================
# Phase 2.5: Line Numbering Edge Cases Tests (diff_generator.py)
# =============================================================================


class TestLineNumberingEdgeCases:
    """Tests for edge cases in line numbering."""

    @pytest.fixture
    def diff_generator(self):
        """Create DiffGenerator with mocked dependencies."""
        from prdiffer.infrastructure.github.diff_generator import DiffGenerator

        mock_diff_utils = Mock()
        return DiffGenerator(diff_utils=mock_diff_utils)

    def test_format_hunk_new_file_start1_zero(self, diff_generator):
        """Test line numbering for new files (start1=0)."""
        hunk = {
            "header": "@@ -0,0 +1,3 @@",
            "new_lines": ["+line1", "+line2", "+line3"],
            "old_lines": [],
            "start1": 0,
            "start2": 1,
        }

        result = diff_generator._format_hunk_with_line_numbers(hunk)

        # Should have new hunk section with proper line numbers starting at 1
        assert "__new hunk__" in result
        assert "1 +line1" in result

    def test_format_hunk_deleted_file(self, diff_generator):
        """Test line numbering for deleted files."""
        hunk = {
            "header": "@@ -1,3 +0,0 @@",
            "new_lines": [],
            "old_lines": ["-line1", "-line2", "-line3"],
            "start1": 1,
            "start2": 0,
        }

        result = diff_generator._format_hunk_with_line_numbers(hunk)

        # Should have old hunk section
        assert "__old hunk__" in result

    def test_format_hunk_empty_no_changes(self, diff_generator):
        """Test that hunks with no changes return empty string."""
        hunk = {
            "header": "@@ -1,3 +1,3 @@",
            "new_lines": [" line1", " line2", " line3"],
            "old_lines": [" line1", " line2", " line3"],
            "start1": 1,
            "start2": 1,
        }

        result = diff_generator._format_hunk_with_line_numbers(hunk)

        # No actual changes, should return empty
        assert result == ""

    def test_format_hunk_only_deletions(self, diff_generator):
        """Test line numbering for hunks with only deletions."""
        hunk = {
            "header": "@@ -1,5 +1,3 @@",
            "new_lines": [" context1", " context2", " context3"],
            "old_lines": [
                " context1",
                "-deleted1",
                "-deleted2",
                " context2",
                " context3",
            ],
            "start1": 1,
            "start2": 1,
        }

        result = diff_generator._format_hunk_with_line_numbers(hunk)

        # Should have both old hunk (deletions) and context in new hunk
        assert "__old hunk__" in result

    def test_extract_hunk_headers_new_file(self, diff_generator):
        """Test header extraction for new file pattern."""

        match = diff_generator.RE_HUNK_HEADER.match("@@ -0,0 +1,3 @@")
        section_header, size1, size2, start1, start2 = (
            diff_generator._extract_hunk_headers(match)
        )

        assert start1 == 0
        assert size1 == 0
        assert start2 == 1
        assert size2 == 3

    def test_extract_hunk_headers_deleted_file(self, diff_generator):
        """Test header extraction for deleted file pattern."""

        match = diff_generator.RE_HUNK_HEADER.match("@@ -1,3 +0,0 @@")
        section_header, size1, size2, start1, start2 = (
            diff_generator._extract_hunk_headers(match)
        )

        assert start1 == 1
        assert size1 == 3
        assert start2 == 0
        assert size2 == 0

    def test_extract_hunk_headers_no_size(self, diff_generator):
        """Test header extraction when size is omitted (defaults to 1)."""

        match = diff_generator.RE_HUNK_HEADER.match("@@ -1 +1 @@")
        section_header, size1, size2, start1, start2 = (
            diff_generator._extract_hunk_headers(match)
        )

        assert start1 == 1
        assert size1 == 1  # Default
        assert start2 == 1
        assert size2 == 1  # Default

    def test_extract_hunk_headers_with_section_header(self, diff_generator):
        """Test header extraction with section header (function name)."""

        match = diff_generator.RE_HUNK_HEADER.match(
            "@@ -10,5 +10,7 @@ def my_function():"
        )
        section_header, size1, size2, start1, start2 = (
            diff_generator._extract_hunk_headers(match)
        )

        assert section_header == "def my_function():"
        assert start1 == 10
        assert start2 == 10


# =============================================================================
# Integration Tests
# =============================================================================


class TestPhase2Integration:
    """Integration tests for Phase 2 improvements."""

    @pytest.mark.asyncio
    async def test_streaming_with_binary_file_handling(self):
        """Test streaming diff generation with binary file handling."""
        from prdiffer.infrastructure.github.diff_generator import DiffGenerator
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils
        from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        diff_utils = DiffUtils()
        generator = DiffGenerator(diff_utils=diff_utils)

        # Create a mix of binary and text files
        files = [
            FilePatchInfo(
                base_file="normal text",
                head_file="modified text",
                patch="@@ -1 +1 @@\n-normal text\n+modified text",
                filename="text.py",
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=1,
                num_minus_lines=1,
            ),
            FilePatchInfo(
                base_file="binary\x00content",
                head_file="new\x00binary",
                patch="@@ binary diff @@",
                filename="binary.bin",
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=1,
                num_minus_lines=1,
            ),
        ]

        results = []
        async for diff in generator.generate_extended_diff_stream(files):
            results.append(diff)

        # Both should be processed (binary file gets marker)
        assert len(results) == 2

    def test_chunked_processing_maintains_diff_integrity(self):
        """Test that chunked processing produces valid diffs."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        # Create original and modified versions
        original_lines = [f"line_{i}" for i in range(200)]
        new_lines = original_lines.copy()
        new_lines[50] = "modified_line_50"
        new_lines[150] = "modified_line_150"

        original = "\n".join(original_lines)
        new = "\n".join(new_lines)

        result = diff_utils.build_full_file_patch_chunked(
            original, new, chunk_size=100, large_file_threshold=100
        )

        # Should detect the modifications
        assert "-line_50" in result or "+modified_line_50" in result
