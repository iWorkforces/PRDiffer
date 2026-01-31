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
from unittest.mock import Mock

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
        diff_patch = "@@ diff"

        result = diff_utils.extend_patch(binary_original, diff_patch, binary_new)
        assert result == "[BINARY FILE - DIFF NOT AVAILABLE]"

    def test_extend_patch_processes_text_files(self):
        """Test that extend_patch processes normal text files."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        diff_utils = DiffUtils()

        original = "line1\nline2"
        new = "line1\nline2\nline3"
        diff_patch = "@@ -1,2 +1,3 @@"

        result = diff_utils.extend_patch(original, diff_patch, new)
        assert result != "[BINARY FILE - DIFF NOT AVAILABLE]"
        assert "@@ -" in result


# =============================================================================
# Phase 2.2: Chunked Processing Tests (diff_utils.py)
# =============================================================================


class TestChunkedProcessing:
    """Tests for chunked processing of large files."""

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

# Tests removed - streaming methods were deprecated and removed


# =============================================================================
# Phase 2.4: Parallel Batch Fetching Tests (api_client.py)
# =============================================================================


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
