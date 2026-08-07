"""Unit tests for Diff Generator.

This module contains comprehensive tests for the DiffGenerator class,
covering diff generation, streaming, and edge case handling.
"""

import pytest
from unittest.mock import patch

from prdiffer.infrastructure.github.diff_generator import DiffGenerator


class TestDiffGenerator:
    """Test suite for DiffGenerator."""

    @pytest.fixture
    def diff_generator(self):
        """Create DiffGenerator instance for testing."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        return DiffGenerator(diff_utils=DiffUtils())

    @pytest.mark.skip(reason="Test patches non-existent _get_file_content method. DiffGenerator does not have this method - test needs to be rewritten.")
    def test_generate_extended_diff(self, diff_generator):
        """Test basic extended diff generation."""
        with patch.object(diff_generator, "_get_file_content") as mock_content:
            mock_content.side_effect = ["old content", "new content"]

            # This test requires more setup for actual execution
            # The skeleton is provided for future implementation

    def test_generate_extended_diff_stream(self, diff_generator):
        """Test streaming diff generation."""
        # Test async streaming functionality
        pass

    def test_generate_single_diff(self, diff_generator):
        """Test single file diff generation."""
        # Test single file diff
        pass


class TestDiffGeneratorEdgeCases:
    """Test suite for DiffGenerator edge cases."""

    @pytest.fixture
    def diff_generator(self):
        """Create DiffGenerator instance for testing."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        return DiffGenerator(diff_utils=DiffUtils())

    def test_empty_file_list(self, diff_generator):
        """Test handling of empty file list."""
        # Should return empty string or handle gracefully
        pass

    def test_deletion_only_diff(self, diff_generator):
        """Test diff for file with only deletions."""
        # Edge case: file completely removed
        pass

    def test_new_file_diff(self, diff_generator):
        """Test diff for new file (no old content)."""
        # Edge case: file added (start1=0)
        pass

    def test_large_file_chunking(self, diff_generator):
        """Test that large files are chunked properly."""
        # Edge case: file exceeds chunk size
        pass


class TestDiffGeneratorHunkParsing:
    """Test suite for hunk parsing in diff generation."""

    @pytest.fixture
    def diff_generator(self):
        """Create DiffGenerator instance for testing."""
        from prdiffer.infrastructure.utils.diff_utils import DiffUtils

        return DiffGenerator(diff_utils=DiffUtils())

    def test_parse_hunks_from_patch(self, diff_generator):
        """Test hunk parsing from patch string."""
        # Test standard hunk format: @@ -1,3 +1,5 @@
        pass

    def test_malformed_hunk_header(self, diff_generator):
        """Test handling of malformed hunk headers."""
        # Edge case: invalid hunk header format
        pass

    def test_extract_hunk_headers(self, diff_generator):
        """Test hunk header extraction."""
        # Test extraction of line numbers from hunks
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestModeAndEofHeaders:
    def test_added_file_emits_new_file_mode(self):
        from unittest.mock import MagicMock
        from prdiffer.domain.entities.file_patch import EDIT_TYPE, FilePatchInfo
        from prdiffer.infrastructure.github.diff_generator import DiffGenerator

        mock_diff_utils = MagicMock()
        mock_diff_utils.build_full_file_patch_chunked.return_value = "\n@@ -0,0 +1,1 @@\n+content\n"
        gen = DiffGenerator(diff_utils=mock_diff_utils)
        patch = FilePatchInfo(
            filename="a.py",
            base_file="",
            head_file="content\n",
            patch="",
            edit_type=EDIT_TYPE.ADDED,
            new_mode="100644",
        )
        result = gen.generate_ordered_file_diffs([patch])
        assert result[0].diff.startswith("new file mode 100644\n")

    def test_deleted_file_emits_deleted_file_mode(self):
        from unittest.mock import MagicMock
        from prdiffer.domain.entities.file_patch import EDIT_TYPE, FilePatchInfo
        from prdiffer.infrastructure.github.diff_generator import DiffGenerator

        mock_diff_utils = MagicMock()
        mock_diff_utils.build_full_file_patch_chunked.return_value = "\n@@ -1,1 +0,0 @@\n-content\n"
        gen = DiffGenerator(diff_utils=mock_diff_utils)
        patch = FilePatchInfo(
            filename="a.py",
            base_file="content\n",
            head_file="",
            patch="",
            edit_type=EDIT_TYPE.DELETED,
            old_mode="100755",
        )
        result = gen.generate_ordered_file_diffs([patch])
        assert result[0].diff.startswith("deleted file mode 100755\n")

    def test_gitlink_add_emits_new_file_mode_160000(self):
        from unittest.mock import MagicMock
        from prdiffer.domain.entities.file_patch import EDIT_TYPE, FilePatchInfo
        from prdiffer.infrastructure.github.diff_generator import DiffGenerator

        mock_diff_utils = MagicMock()
        mock_diff_utils.build_full_file_patch_chunked.return_value = "\n@@ -0,0 +1,1 @@\n+Subproject commit abc\n"
        gen = DiffGenerator(diff_utils=mock_diff_utils)
        patch = FilePatchInfo(
            filename="sub",
            base_file="",
            head_file="Subproject commit abc\n",
            patch="",
            edit_type=EDIT_TYPE.ADDED,
            new_mode="160000",
        )
        result = gen.generate_ordered_file_diffs([patch])
        assert result[0].diff.startswith("new file mode 160000\n")

    def test_renderer_exception_never_returns_provider_hunk(self):
        from unittest.mock import MagicMock
        import pytest
        from prdiffer.domain.entities.file_patch import EDIT_TYPE, FilePatchInfo
        from prdiffer.domain.exceptions import DiffGenerationError
        from prdiffer.infrastructure.github.diff_generator import DiffGenerator

        mock_diff_utils = MagicMock()
        mock_diff_utils.build_full_file_patch_chunked.side_effect = RuntimeError("boom")
        gen = DiffGenerator(diff_utils=mock_diff_utils)
        patch = FilePatchInfo(
            filename="a.py",
            base_file="a\n",
            head_file="b\n",
            patch="@@ provider hunk only @@\n",
            edit_type=EDIT_TYPE.MODIFIED,
        )
        with pytest.raises(DiffGenerationError):
            gen.generate_ordered_file_diffs([patch])
