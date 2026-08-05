"""Comprehensive tests for DiffGenerator."""

import pytest
from unittest.mock import MagicMock

from prdiffer.infrastructure.github.diff_generator import (
    DiffGenerator,
    get_diff_generator,
)
from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE


@pytest.fixture
def mock_diff_utils():
    """Create mock diff utils."""
    mock = MagicMock()
    mock.extend_patch.return_value = "extended patch content"
    return mock


@pytest.fixture
def mock_parallel_executor():
    """Create mock parallel executor."""
    mock = MagicMock()
    mock.max_workers = 4
    mock.execute_batch.return_value = []
    return mock


@pytest.fixture
def sample_file_patch():
    """Create sample FilePatchInfo."""
    return FilePatchInfo(
        filename="src/test.py",
        base_file="old content\nline1\nline2\n",
        head_file="new content\nline1\nline2 modified\nline3\n",
        patch="@@ -1,3 +1,4 @@\n-old content\n+new content\n line1\n line2\n+line3\n",
        edit_type=EDIT_TYPE.MODIFIED,
        num_plus_lines=2,
        num_minus_lines=1,
    )


@pytest.fixture
def sample_file_patches(sample_file_patch):
    """Create list of sample FilePatchInfo objects."""
    return [
        sample_file_patch,
        FilePatchInfo(
            filename="src/new_file.py",
            base_file="",
            head_file="new file content\n",
            patch="@@ -0,0 +1 @@\n+new file content\n",
            edit_type=EDIT_TYPE.ADDED,
            num_plus_lines=1,
            num_minus_lines=0,
        ),
    ]


class TestDiffGeneratorInit:
    """Tests for DiffGenerator initialization."""

    def test_init_with_defaults(self, mock_diff_utils):
        """Test initialization with default parameters."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)

        assert generator._diff_utils is mock_diff_utils
        assert generator._parallel_executor is None
        # Parallel ordered generation no longer requires an injected executor.
        assert generator._parallel_enabled is True
        assert generator._parallel_threshold == 3

    def test_init_with_parallel_executor(self, mock_diff_utils, mock_parallel_executor):
        """Test initialization with parallel executor."""
        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            parallel_executor=mock_parallel_executor,
            parallel_enabled=True,
        )

        assert generator._parallel_executor is mock_parallel_executor
        assert generator._parallel_enabled is True

    def test_init_parallel_disabled(self, mock_diff_utils, mock_parallel_executor):
        """Test that parallel can be disabled even with executor."""
        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            parallel_executor=mock_parallel_executor,
            parallel_enabled=False,
        )

        assert generator._parallel_enabled is False

    def test_init_custom_threshold(self, mock_diff_utils):
        """Test custom parallel threshold."""
        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            parallel_threshold=5,
        )

        assert generator._parallel_threshold == 5

    def test_init_custom_logger(self, mock_diff_utils):
        """Test initialization with custom logger."""
        mock_logger = MagicMock()
        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            logger=mock_logger,
        )

        assert generator._logger is mock_logger


class TestGenerateExtendedDiff:
    """Tests for generate_extended_diff method."""

    def test_empty_file_list(self, mock_diff_utils):
        """Test with empty file list."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        result = generator.generate_extended_diff([])

        assert result == []

    def test_sequential_processing_below_threshold(self, mock_diff_utils, sample_file_patch):
        """Strict path builds full context from base/head (not provider hunk alone)."""
        mock_diff_utils.build_full_file_patch_chunked.return_value = "\n@@ -1 +1 @@\n-old\n+new"
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        result = generator.generate_extended_diff([sample_file_patch])

        assert len(result) == 1
        mock_diff_utils.build_full_file_patch_chunked.assert_called()

    def test_sequential_processing_parallel_disabled(self, mock_diff_utils, mock_parallel_executor, sample_file_patches):
        """Ordered generation does not depend on the legacy parallel executor."""
        mock_diff_utils.build_full_file_patch_chunked.return_value = "\n@@ -1 +1 @@\n-old\n+new"
        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            parallel_executor=mock_parallel_executor,
            parallel_enabled=False,
        )
        result = generator.generate_extended_diff(sample_file_patches)

        assert len(result) == 2
        assert mock_parallel_executor.execute_batch.call_count == 0

    def test_parallel_flag_still_returns_one_result_per_file(self, mock_diff_utils, mock_parallel_executor):
        """Even with parallel enabled, strict ordered generation returns N results."""
        mock_diff_utils.build_full_file_patch_chunked.return_value = "\n@@ -1 +1 @@\n-old\n+new"
        files = [
            FilePatchInfo(
                filename=f"file{i}.py",
                base_file="old",
                head_file="new",
                patch=f"patch{i}",
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=1,
                num_minus_lines=1,
            )
            for i in range(5)
        ]

        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            parallel_executor=mock_parallel_executor,
            parallel_enabled=True,
            parallel_threshold=3,
        )
        result = generator.generate_extended_diff(files)

        assert len(result) == 5

    def test_file_without_patch_recovered_from_content(self, mock_diff_utils):
        """Missing provider patch is recovered from complete base/head text."""
        mock_diff_utils.build_full_file_patch_chunked.return_value = "\n@@ -1 +1 @@\n-old\n+new"
        file_no_patch = FilePatchInfo(
            filename="empty.py",
            base_file="old\n",
            head_file="new\n",
            patch="",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=1,
            num_minus_lines=1,
        )

        generator = DiffGenerator(diff_utils=mock_diff_utils)
        result = generator.generate_extended_diff([file_no_patch])

        assert len(result) == 1
        assert result[0]

    def test_with_line_numbers(self, mock_diff_utils, sample_file_patch):
        """Test generation with line numbers."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        result = generator.generate_extended_diff([sample_file_patch], add_line_numbers_to_hunks=True)

        assert len(result) == 1
        assert "Full file path:" in result[0]


class TestHunkParsing:
    """Tests for hunk parsing methods."""

    def test_parse_hunks_standard_format(self, mock_diff_utils):
        """Test parsing standard hunk format."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        patch_lines = [
            "@@ -1,3 +1,4 @@",
            "-old line",
            "+new line",
            " context line",
        ]

        hunks = generator._parse_hunks_from_patch(patch_lines)

        assert len(hunks) == 1
        assert hunks[0]["start1"] == 1
        assert hunks[0]["start2"] == 1
        assert len(hunks[0]["old_lines"]) == 2
        assert len(hunks[0]["new_lines"]) == 2

    def test_parse_hunks_new_file(self, mock_diff_utils):
        """Test parsing hunk for new file (start1=0)."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        patch_lines = [
            "@@ -0,0 +1,5 @@",
            "+line1",
            "+line2",
            "+line3",
        ]

        hunks = generator._parse_hunks_from_patch(patch_lines)

        assert len(hunks) == 1
        assert hunks[0]["start1"] == 0
        assert hunks[0]["start2"] == 1

    def test_parse_hunks_deleted_file(self, mock_diff_utils):
        """Test parsing hunk for deleted file."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        patch_lines = [
            "@@ -1,3 +0,0 @@",
            "-line1",
            "-line2",
            "-line3",
        ]

        hunks = generator._parse_hunks_from_patch(patch_lines)

        assert len(hunks) == 1
        assert hunks[0]["start1"] == 1
        assert hunks[0]["start2"] == 0

    def test_parse_multiple_hunks(self, mock_diff_utils):
        """Test parsing multiple hunks in one patch."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        patch_lines = [
            "@@ -1,3 +1,3 @@",
            " context",
            "@@ -10,5 +10,5 @@",
            " more context",
        ]

        hunks = generator._parse_hunks_from_patch(patch_lines)

        assert len(hunks) == 2

    def test_skip_no_newline_marker(self, mock_diff_utils):
        """Test that 'no newline at end of file' markers are skipped."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        patch_lines = [
            "@@ -1,2 +1,2 @@",
            "-old line",
            "\\ No newline at end of file",
            "+new line",
        ]

        hunks = generator._parse_hunks_from_patch(patch_lines)

        assert len(hunks) == 1
        assert "\\ No newline" not in str(hunks[0]["old_lines"])
        assert "\\ No newline" not in str(hunks[0]["new_lines"])

    def test_empty_patch(self, mock_diff_utils):
        """Test parsing empty patch."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        hunks = generator._parse_hunks_from_patch([])

        assert hunks == []


class TestExtractHunkHeaders:
    """Tests for _extract_hunk_headers method."""

    def test_standard_header(self, mock_diff_utils):
        """Test extracting standard hunk header."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        import re

        match = re.match(generator.RE_HUNK_HEADER, "@@ -1,3 +1,5 @@ function")

        section, size1, size2, start1, start2 = generator._extract_hunk_headers(match)

        assert start1 == 1
        assert size1 == 3
        assert start2 == 1
        assert size2 == 5
        assert section == "function"

    def test_header_without_sizes(self, mock_diff_utils):
        """Test header without explicit sizes (default to 1)."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        import re

        match = re.match(generator.RE_HUNK_HEADER, "@@ -1 +1 @@")

        section, size1, size2, start1, start2 = generator._extract_hunk_headers(match)

        assert start1 == 1
        assert size1 == 1
        assert start2 == 1
        assert size2 == 1

    def test_new_file_header(self, mock_diff_utils):
        """Test header for new file."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        import re

        match = re.match(generator.RE_HUNK_HEADER, "@@ -0,0 +1,10 @@")

        section, size1, size2, start1, start2 = generator._extract_hunk_headers(match)

        assert start1 == 0
        assert size1 == 0
        assert start2 == 1
        assert size2 == 10

    def test_deleted_file_header(self, mock_diff_utils):
        """Test header for deleted file."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        import re

        match = re.match(generator.RE_HUNK_HEADER, "@@ -1,5 +0,0 @@")

        section, size1, size2, start1, start2 = generator._extract_hunk_headers(match)

        assert start1 == 1
        assert size1 == 5
        assert start2 == 0
        assert size2 == 0


class TestFormatHunkWithLineNumbers:
    """Tests for _format_hunk_with_line_numbers method."""

    def test_format_standard_hunk(self, mock_diff_utils):
        """Test formatting a standard hunk with changes."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        hunk = {
            "header": "@@ -1,3 +1,3 @@",
            "new_lines": ["+added", " context"],
            "old_lines": ["-removed", " context"],
            "start1": 1,
            "start2": 1,
        }

        result = generator._format_hunk_with_line_numbers(hunk)

        assert "@@" in result
        assert "__new hunk__" in result
        assert "__old hunk__" in result

    def test_format_deletion_only_hunk(self, mock_diff_utils):
        """Test formatting a deletion-only hunk."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        hunk = {
            "header": "@@ -1,1 +0,0 @@",
            "new_lines": [],
            "old_lines": ["-removed line"],
            "start1": 1,
            "start2": 0,
        }

        result = generator._format_hunk_with_line_numbers(hunk)

        assert "@@" in result
        assert "__old hunk__" in result

    def test_format_no_changes_hunk(self, mock_diff_utils):
        """Test formatting a hunk with no actual changes."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        hunk = {
            "header": "@@ -1,3 +1,3 @@",
            "new_lines": [" context1", " context2"],
            "old_lines": [" context1", " context2"],
            "start1": 1,
            "start2": 1,
        }

        result = generator._format_hunk_with_line_numbers(hunk)

        assert result == ""

    def test_format_new_file_hunk(self, mock_diff_utils):
        """Test formatting a new file hunk."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        hunk = {
            "header": "@@ -0,0 +1,5 @@",
            "new_lines": ["+line1", "+line2", "+line3"],
            "old_lines": [],
            "start1": 0,
            "start2": 1,
        }

        result = generator._format_hunk_with_line_numbers(hunk)

        assert "@@" in result
        assert "__new hunk__" in result
        assert "__old hunk__" not in result


class TestGenerateFileHeader:
    """Tests for _generate_file_header method."""

    def test_first_file_header(self, mock_diff_utils, sample_file_patch):
        """Test header for first file (no separator)."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)

        result = generator._generate_file_header(sample_file_patch, is_first_file=True)

        assert result.startswith("\n")
        assert "Full file path:" in result
        assert sample_file_patch.filename in result
        assert "---" not in result

    def test_subsequent_file_header(self, mock_diff_utils, sample_file_patch):
        """Test header for subsequent files (with separator)."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)

        result = generator._generate_file_header(sample_file_patch, is_first_file=False)

        assert "---" in result
        assert sample_file_patch.filename in result

    def test_none_file(self, mock_diff_utils):
        """Test header with None file."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)

        result = generator._generate_file_header(None, is_first_file=True)

        assert result == ""


class TestAddLineToHunk:
    """Tests for _add_line_to_hunk method."""

    def test_add_added_line(self, mock_diff_utils):
        """Test adding a line that starts with +."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        hunk = {"new_lines": [], "old_lines": []}

        generator._add_line_to_hunk(hunk, "+new line", 0, ["+new line"])

        assert "+new line" in hunk["new_lines"]
        assert "+new line" not in hunk["old_lines"]

    def test_add_removed_line(self, mock_diff_utils):
        """Test adding a line that starts with -."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        hunk = {"new_lines": [], "old_lines": []}

        generator._add_line_to_hunk(hunk, "-old line", 0, ["-old line"])

        assert "-old line" in hunk["old_lines"]
        assert "-old line" not in hunk["new_lines"]

    def test_add_context_line(self, mock_diff_utils):
        """Test adding a context line."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        hunk = {"new_lines": [], "old_lines": []}

        generator._add_line_to_hunk(hunk, " context", 0, [" context"])

        assert " context" in hunk["new_lines"]
        assert " context" in hunk["old_lines"]

    def test_skip_empty_before_hunk_header(self, mock_diff_utils):
        """Test that empty lines before hunk headers are skipped."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        hunk = {"new_lines": [], "old_lines": []}

        generator._add_line_to_hunk(hunk, "", 0, ["", "@@ -1,3 +1,3 @@"])

        assert hunk["new_lines"] == [""]
        assert hunk["old_lines"] == [""]

    def test_skip_empty_at_end(self, mock_diff_utils):
        """Test that empty lines at end are skipped."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        hunk = {"new_lines": [], "old_lines": []}

        generator._add_line_to_hunk(hunk, "", 0, [""])

        assert hunk["new_lines"] == [""]
        assert hunk["old_lines"] == [""]


class TestProcessSingleFileForDiff:
    """Tests for _process_single_file_for_diff method."""

    def test_process_file_success(self, mock_diff_utils, sample_file_patch):
        """Test successful file processing."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        indexed_data = (0, sample_file_patch, False, 1)

        result = generator._process_single_file_for_diff(indexed_data)

        assert result is not None
        assert result[0] == 0
        assert "Full file path:" in result[1]

    def test_process_file_with_line_numbers(self, mock_diff_utils, sample_file_patch):
        """Test file processing with line numbers."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        indexed_data = (0, sample_file_patch, True, 1)

        result = generator._process_single_file_for_diff(indexed_data)

        assert result is not None
        assert "Full file path:" in result[1]

    def test_process_file_no_patch(self, mock_diff_utils):
        """Test processing file with no patch."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        file_no_patch = FilePatchInfo(
            filename="empty.py",
            base_file="",
            head_file="",
            patch="",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=0,
            num_minus_lines=0,
        )
        indexed_data = (0, file_no_patch, False, 1)

        result = generator._process_single_file_for_diff(indexed_data)

        assert result is None

    def test_process_file_extend_patch_fails(self, mock_diff_utils, sample_file_patch):
        """Test handling when extend_patch returns None."""
        mock_diff_utils.extend_patch.return_value = None
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        indexed_data = (0, sample_file_patch, False, 1)

        result = generator._process_single_file_for_diff(indexed_data)

        assert result is None

    def test_process_file_exception(self, mock_diff_utils, sample_file_patch):
        """Test exception handling during file processing."""
        mock_diff_utils.extend_patch.side_effect = Exception("Test error")
        generator = DiffGenerator(diff_utils=mock_diff_utils)
        indexed_data = (0, sample_file_patch, False, 1)

        result = generator._process_single_file_for_diff(indexed_data)

        assert result is None


class TestGenerateExtendedDiffParallel:
    """Tests for _generate_extended_diff_parallel method."""

    def test_fallback_when_no_executor(self, mock_diff_utils, sample_file_patches):
        """Test fallback to sequential when no executor available."""
        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            parallel_executor=None,
        )

        result = generator._generate_extended_diff_parallel(sample_file_patches, False)

        assert len(result) == 2

    def test_parallel_processing_success(self, mock_diff_utils, mock_parallel_executor, sample_file_patches):
        """Test successful parallel processing."""
        mock_parallel_executor.execute_batch.return_value = [
            (0, "diff_content_0"),
            (1, "diff_content_1"),
        ]

        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            parallel_executor=mock_parallel_executor,
        )

        result = generator._generate_extended_diff_parallel(sample_file_patches, False)

        assert len(result) == 2

    def test_parallel_processing_with_none_results(self, mock_diff_utils, mock_parallel_executor):
        """Test parallel processing with some None results."""
        files = [
            FilePatchInfo(
                filename=f"file{i}.py",
                base_file="old",
                head_file="new",
                patch=f"patch{i}",
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=1,
                num_minus_lines=1,
            )
            for i in range(3)
        ]

        mock_parallel_executor.execute_batch.return_value = [
            (0, "diff0"),
            None,
            (2, "diff2"),
        ]

        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            parallel_executor=mock_parallel_executor,
        )

        result = generator._generate_extended_diff_parallel(files, False)

        assert len(result) == 2
        assert result[0] == "diff0"
        assert result[1] == "diff2"


class TestGetDiffGenerator:
    """Tests for get_diff_generator factory function."""

    def test_get_diff_generator_defaults(self, mock_diff_utils):
        """Test factory with default parameters."""
        generator = get_diff_generator(diff_utils=mock_diff_utils)

        assert generator._diff_utils is mock_diff_utils
        assert generator._parallel_threshold == 3

    def test_get_diff_generator_custom_params(self, mock_diff_utils, mock_parallel_executor):
        """Test factory with custom parameters."""
        generator = get_diff_generator(
            diff_utils=mock_diff_utils,
            parallel_executor=mock_parallel_executor,
            parallel_enabled=False,
            parallel_threshold=5,
        )

        assert generator._parallel_enabled is False
        assert generator._parallel_threshold == 5


class TestDecoupleAndConvertToHunksWithLineNumbers:
    """Tests for _decouple_and_convert_to_hunks_with_lines_numbers method."""

    def test_basic_conversion(self, mock_diff_utils, sample_file_patch):
        """Test basic conversion with line numbers."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)

        result = generator._decouple_and_convert_to_hunks_with_lines_numbers(
            sample_file_patch.patch,
            sample_file_patch,
            is_first_file=True,
        )

        assert "Full file path:" in result
        assert sample_file_patch.filename in result

    def test_subsequent_file(self, mock_diff_utils, sample_file_patch):
        """Test conversion for subsequent file (with separator)."""
        generator = DiffGenerator(diff_utils=mock_diff_utils)

        result = generator._decouple_and_convert_to_hunks_with_lines_numbers(
            sample_file_patch.patch,
            sample_file_patch,
            is_first_file=False,
        )

        assert "---" in result


class TestSequentialVsParallel:
    """Tests comparing sequential vs parallel processing."""

    def test_below_threshold_always_sequential(self, mock_diff_utils, mock_parallel_executor):
        """Test that files below threshold always use sequential."""
        files = [
            FilePatchInfo(
                filename="file.py",
                base_file="old",
                head_file="new",
                patch="patch",
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=1,
                num_minus_lines=1,
            )
        ]

        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            parallel_executor=mock_parallel_executor,
            parallel_enabled=True,
            parallel_threshold=3,
        )

        generator.generate_extended_diff(files)

        mock_parallel_executor.execute_batch.assert_not_called()

    def test_at_threshold_returns_ordered_results(self, mock_diff_utils, mock_parallel_executor):
        """Strict ordered generation returns one result per file regardless of parallel flags."""
        mock_diff_utils.build_full_file_patch_chunked.return_value = "\n@@ -1 +1 @@\n-old\n+new"
        files = [
            FilePatchInfo(
                filename=f"file{i}.py",
                base_file="old",
                head_file="new",
                patch=f"patch{i}",
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=1,
                num_minus_lines=1,
            )
            for i in range(3)
        ]

        generator = DiffGenerator(
            diff_utils=mock_diff_utils,
            parallel_executor=mock_parallel_executor,
            parallel_enabled=True,
            parallel_threshold=3,
        )

        result = generator.generate_extended_diff(files)
        assert len(result) == 3
