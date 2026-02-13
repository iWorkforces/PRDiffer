"""Unit tests for FilePatchInfo entity.

Tests the FilePatchInfo dataclass which represents file changes in a pull request.
"""

from prdiffer.domain.entities.file_patch import (
    FilePatchInfo,
    EDIT_TYPE,
)


class TestFilePatchInfoCreation:
    """Test suite for FilePatchInfo creation and initialization."""

    def test_file_patch_info_creation_minimal(self):
        """Test creating a FilePatchInfo with only required fields."""
        patch = FilePatchInfo(filename="src/example.py")

        assert patch.filename == "src/example.py"
        assert patch.base_file == ""
        assert patch.head_file == ""
        assert patch.patch == ""
        assert patch.edit_type == EDIT_TYPE.UNKNOWN
        assert patch.num_plus_lines == 0
        assert patch.num_minus_lines == 0
        assert patch.language is None
        assert patch.old_filename is None
        assert patch.ai_file_summary is None
        assert patch.tokens == -1

    def test_file_patch_info_creation_full(self):
        """Test creating a FilePatchInfo with all fields."""
        patch = FilePatchInfo(
            filename="src/example.py",
            patch="@@ -1,3 +1,5 @@\n-old\n+new\n",
            base_file="old content",
            head_file="new content",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=5,
            num_minus_lines=3,
            language="Python",
            old_filename="src/old_example.py",
            ai_file_summary="Added new feature",
            tokens=1000,
            diff_metadata={"hunks": 1},
            code_smell_indicators=("Contains TODO comments",),
            suggested_review_priority="high",
        )

        assert patch.filename == "src/example.py"
        assert patch.patch == "@@ -1,3 +1,5 @@\n-old\n+new\n"
        assert patch.base_file == "old content"
        assert patch.head_file == "new content"
        assert patch.edit_type == EDIT_TYPE.MODIFIED
        assert patch.num_plus_lines == 5
        assert patch.num_minus_lines == 3
        assert patch.language == "Python"
        assert patch.old_filename == "src/old_example.py"
        assert patch.ai_file_summary == "Added new feature"
        assert patch.tokens == 1000
        assert patch.diff_metadata == {"hunks": 1}
        assert patch.code_smell_indicators == ("Contains TODO comments",)
        assert patch.suggested_review_priority == "high"

    def test_computed_properties_initialized(self):
        """Test that computed properties are initialized after creation."""
        patch = FilePatchInfo(
            filename="src/test.py",
            base_file="line1\nline2\nline3",
            head_file="line1\nline2\nnew\n",
            num_plus_lines=1,
            num_minus_lines=1,
        )

        # Computed properties should be set
        assert patch._file_extension == ".py"
        assert patch._is_binary is False
        assert 0.0 <= patch._change_percentage <= 100.0

    def test_default_review_priority(self):
        """Test default review priority is 'normal'."""
        patch = FilePatchInfo(filename="test.py")

        assert patch.suggested_review_priority == "normal"


class TestEDITTypeEnum:
    """Test suite for EDIT_TYPE enumeration."""

    def test_edit_type_enum_values(self):
        """Test that EDIT_TYPE enum has correct values."""
        assert EDIT_TYPE.ADDED.value == "added"
        assert EDIT_TYPE.DELETED.value == "deleted"
        assert EDIT_TYPE.MODIFIED.value == "modified"
        assert EDIT_TYPE.RENAMED.value == "renamed"
        assert EDIT_TYPE.UNKNOWN.value == "unknown"

    def test_edit_type_comparison(self):
        """Test EDIT_TYPE equality comparison."""
        assert EDIT_TYPE.ADDED == EDIT_TYPE.ADDED
        assert EDIT_TYPE.MODIFIED != EDIT_TYPE.ADDED
        assert EDIT_TYPE.UNKNOWN == EDIT_TYPE.UNKNOWN


class TestFilePatchInfoProperties:
    """Test suite for FilePatchInfo property methods."""

    def test_file_extension_property(self):
        """Test file_extension property."""
        patch = FilePatchInfo(filename="src/main.py")

        assert patch.file_extension == ".py"

    def test_file_extension_none(self):
        """Test file_extension for files without extension."""
        patch = FilePatchInfo(filename="Dockerfile")

        assert patch.file_extension is None

    def test_file_extension_multiple_dots(self):
        """Test file_extension with multiple dots."""
        patch = FilePatchInfo(filename="src/main.test.js")

        assert patch.file_extension == ".js"

    def test_is_binary_property_binary_extension(self):
        """Test is_binary for known binary extensions."""
        patch = FilePatchInfo(filename="image.png")

        assert patch.is_binary is True

    def test_is_binary_property_text_file(self):
        """Test is_binary for text files."""
        patch = FilePatchInfo(filename="readme.txt", head_file="This is a text file")

        assert patch.is_binary is False

    def test_change_percentage_property(self):
        """Test change_percentage calculation."""
        patch = FilePatchInfo(
            filename="test.py",
            base_file="line1\nline2\nline3\nline4\nline5\n",
            num_plus_lines=2,
            num_minus_lines=1,
        )

        # 3 changes out of 5 original lines = 60%
        assert patch.change_percentage == 60.0

    def test_change_percentage_zero(self):
        """Test change_percentage when no changes."""
        patch = FilePatchInfo(
            filename="test.py",
            base_file="line1\nline2\nline3",
            num_plus_lines=0,
            num_minus_lines=0,
        )

        assert patch.change_percentage == 0.0

    def test_change_percentage_capped_at_100(self):
        """Test change_percentage is capped at 100%."""
        patch = FilePatchInfo(
            filename="test.py",
            base_file="line1",
            num_plus_lines=100,
            num_minus_lines=50,
        )

        assert patch.change_percentage == 100.0

    def test_total_changes_property(self):
        """Test total_changes property."""
        patch = FilePatchInfo(
            filename="test.py",
            num_plus_lines=10,
            num_minus_lines=5,
        )

        assert patch.total_changes == 15

    def test_is_significant_change_large_changes(self):
        """Test is_significant_change for large changes."""
        patch = FilePatchInfo(
            filename="test.py",
            num_plus_lines=51,
            num_minus_lines=0,
        )

        assert patch.is_significant_change is True

    def test_is_significant_change_file_addition(self):
        """Test is_significant_change for added files."""
        patch = FilePatchInfo(
            filename="test.py",
            edit_type=EDIT_TYPE.ADDED,
        )

        assert patch.is_significant_change is True

    def test_is_significant_change_file_deletion(self):
        """Test is_significant_change for deleted files."""
        patch = FilePatchInfo(
            filename="test.py",
            edit_type=EDIT_TYPE.DELETED,
        )

        assert patch.is_significant_change is True

    def test_is_significant_change_renamed_file(self):
        """Test is_significant_change for renamed files."""
        patch = FilePatchInfo(
            filename="test.py",
            edit_type=EDIT_TYPE.RENAMED,
        )

        assert patch.is_significant_change is True

    def test_is_significant_change_small_changes(self):
        """Test is_significant_change for small changes."""
        patch = FilePatchInfo(
            filename="test.py",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=10,
            num_minus_lines=5,
        )

        assert patch.is_significant_change is False


class TestFilePatchInfoMethods:
    """Test suite for FilePatchInfo methods."""

    def test_get_summary(self):
        """Test get_summary returns complete summary."""
        patch = FilePatchInfo(
            filename="src/test.py",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=10,
            num_minus_lines=5,
            language="Python",
            base_file="line1\nline2\nline3\nline4\nline5\n",
        )

        summary = patch.get_summary()

        assert summary["filename"] == "src/test.py"
        assert summary["edit_type"] == EDIT_TYPE.MODIFIED
        assert summary["total_changes"] == 15
        assert summary["additions"] == 10
        assert summary["deletions"] == 5
        assert summary["language"] == "Python"
        assert summary["is_binary"] is False
        assert summary["is_significant"] is False
        assert summary["file_extension"] == ".py"
        assert summary["review_priority"] == "normal"

    def test_calculate_review_priority_high(self):
        """Test calculate_review_priority for security files."""
        patch = FilePatchInfo(filename="src/security/auth.py")

        priority = patch.calculate_review_priority()

        assert priority == "high"

    def test_calculate_review_priority_high_config(self):
        """Test calculate_review_priority for config files."""
        patch = FilePatchInfo(filename="config/database.py")

        priority = patch.calculate_review_priority()

        assert priority == "high"

    def test_calculate_review_priority_high_large_changes(self):
        """Test calculate_review_priority for large changes."""
        patch = FilePatchInfo(
            filename="src/main.py", num_plus_lines=101, num_minus_lines=0
        )

        priority = patch.calculate_review_priority()

        assert priority == "high"

    def test_calculate_review_priority_low_test_file(self):
        """Test calculate_review_priority for test files."""
        patch = FilePatchInfo(filename="tests/test_main.py")

        priority = patch.calculate_review_priority()

        assert priority == "low"

    def test_calculate_review_priority_low_markdown(self):
        """Test calculate_review_priority for markdown files."""
        patch = FilePatchInfo(filename="README.md")

        priority = patch.calculate_review_priority()

        assert priority == "low"

    def test_calculate_review_priority_normal(self):
        """Test calculate_review_priority for normal files."""
        patch = FilePatchInfo(filename="src/main.py")

        priority = patch.calculate_review_priority()

        assert priority == "normal"

    def test_detect_code_smells_empty_patch(self):
        """Test detect_code_smells with empty patch."""
        patch = FilePatchInfo(filename="test.py", patch="")

        smells = patch.detect_code_smells()

        assert smells == []

    def test_detect_code_smells_todo(self):
        """Test detect_code_smells detects TODO."""
        patch = FilePatchInfo(
            filename="test.py",
            patch="@@ -1,1 +1,2 @@\n+new code  # TODO: fix this\n",
        )

        smells = patch.detect_code_smells()

        assert "Contains TODO comments" in smells

    def test_detect_code_smells_console_log(self):
        """Test detect_code_smells detects console.log."""
        patch = FilePatchInfo(
            filename="test.js",
            patch="@@ -1,1 +1,2 @@\n+console.log('debug')\n",
        )

        smells = patch.detect_code_smells()

        assert "Contains debug console.log" in smells

    def test_detect_code_smells_print(self):
        """Test detect_code_smells detects print statements."""
        patch = FilePatchInfo(
            filename="test.py",
            patch="@@ -1,1 +1,2 @@\n+print('debug')\n",
        )

        smells = patch.detect_code_smells()

        assert "Contains debug print statements" in smells

    def test_detect_code_smells_large_change(self):
        """Test detect_code_smells for very large changes."""
        # Note: detect_code_smells only checks patch content for code smells
        # The large change check is only done when there's a patch
        patch = FilePatchInfo(
            filename="test.py",
            num_plus_lines=600,
            num_minus_lines=0,
            patch="@@ -1,1 +1,600 @@\n+many lines\n",
        )

        smells = patch.detect_code_smells()

        # Should detect both the large change and have the patch
        assert len(smells) >= 1
        assert any("Very large change set" in s for s in smells)

    def test_detect_code_smells_deleted_file(self):
        """Test detect_code_smells for deleted files."""
        patch = FilePatchInfo(
            filename="test.py", edit_type=EDIT_TYPE.DELETED, patch="@@ -1,5 +0,0 @@"
        )

        smells = patch.detect_code_smells()

        assert "File deleted" in smells[0]

    def test_validate_valid(self):
        """Test validate with valid data."""
        patch = FilePatchInfo(
            filename="test.py",
            num_plus_lines=10,
            num_minus_lines=5,
            edit_type=EDIT_TYPE.MODIFIED,
        )

        errors = patch.validate()

        assert errors == []

    def test_validate_empty_filename(self):
        """Test validate with empty filename."""
        patch = FilePatchInfo(filename="   ")

        errors = patch.validate()

        assert len(errors) > 0
        assert any("Filename cannot be empty" in e for e in errors)

    def test_validate_negative_plus_lines(self):
        """Test validate with negative plus lines."""
        patch = FilePatchInfo(filename="test.py", num_plus_lines=-1)

        errors = patch.validate()

        assert len(errors) > 0
        assert any("plus lines" in e for e in errors)

    def test_validate_renamed_without_old_filename(self):
        """Test validate for renamed file without old filename."""
        patch = FilePatchInfo(
            filename="new.py", edit_type=EDIT_TYPE.RENAMED, old_filename=None
        )

        errors = patch.validate()

        assert len(errors) > 0
        assert any("Old filename is required" in e for e in errors)

    def test_is_ignored_file_no_patterns(self):
        """Test is_ignored_file with no patterns."""
        patch = FilePatchInfo(filename="test.py")

        assert patch.is_ignored_file() is False

    def test_is_ignored_file_with_match(self):
        """Test is_ignored_file with matching pattern."""
        # Note: is_ignored_file checks if pattern substring is in filename
        # Not glob pattern matching - "lock" is in "package-lock.json"
        patch = FilePatchInfo(filename="package-lock.json")

        assert patch.is_ignored_file(["lock", "node_modules"]) is True

    def test_is_ignored_file_no_match(self):
        """Test is_ignored_file with no matching pattern."""
        patch = FilePatchInfo(filename="src/main.py")

        assert patch.is_ignored_file(["*.lock", "node_modules/"]) is False

    def test_get_diff_statistics_empty_patch(self):
        """Test get_diff_statistics with empty patch."""
        patch = FilePatchInfo(filename="test.py", patch="")

        stats = patch.get_diff_statistics()

        assert stats["hunks"] == 0
        assert stats["context_lines"] == 0
        assert stats["addition_lines"] == 0
        assert stats["deletion_lines"] == 0
        assert stats["diff_lines"] == []
        # Note: total_diff_lines is not a key in the returned dict
        assert len(stats["diff_lines"]) == 0

    def test_get_diff_statistics_with_content(self):
        """Test get_diff_statistics parses diff correctly."""
        patch = FilePatchInfo(
            filename="test.py",
            patch="""@@ -1,3 +1,5 @@
 context line
-old line
+new line 1
+new line 2
 context line
""",
        )

        stats = patch.get_diff_statistics()

        assert stats["hunks"] == 1
        assert stats["context_lines"] == 2
        assert stats["addition_lines"] == 2
        assert stats["deletion_lines"] == 1
        assert stats["total_diff_lines"] == 6

    def test_format_for_display_empty_patch(self):
        """Test format_for_display with empty patch."""
        patch = FilePatchInfo(filename="test.py", patch="")

        result = patch.format_for_display()

        assert "Empty diff" in result
        assert "test.py" in result

    def test_format_for_display_short_patch(self):
        """Test format_for_display with short patch."""
        patch = FilePatchInfo(
            filename="test.py",
            patch="@@ -1,1 +1,2 @@\n-old\n+new\n",
        )

        result = patch.format_for_display()

        assert "@@" in result
        assert result == patch.patch  # Short patches returned as-is

    def test_format_for_display_long_patch(self):
        """Test format_for_display truncates long patches."""
        lines = [f"line {i}" for i in range(20)]
        patch = FilePatchInfo(filename="test.py", patch="\n".join(lines))

        result = patch.format_for_display(max_context_lines=10)

        assert "..." in result  # Should be truncated
        # Should have first 5 lines, ..., last 5 lines (5 + 1 (...) + 5 = 11)
        result_lines = result.split("\n")
        assert len(result_lines) == 11  # 5 + 1 (...) + 5


class TestFilePatchInfoEquality:
    """Test FilePatchInfo equality behavior."""

    def test_equality_all_fields_match(self):
        """Test equality when all fields match."""
        patch1 = FilePatchInfo(
            filename="test.py",
            patch="patch1",
            base_file="base",
            head_file="head",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=1,
            num_minus_lines=1,
        )

        patch2 = FilePatchInfo(
            filename="test.py",
            patch="patch1",
            base_file="base",
            head_file="head",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=1,
            num_minus_lines=1,
        )

        assert patch1 == patch2

    def test_inequality_different_filename(self):
        """Test inequality with different filenames."""
        patch1 = FilePatchInfo(filename="file1.py")
        patch2 = FilePatchInfo(filename="file2.py")

        assert patch1 != patch2

    def test_inequality_different_fields(self):
        """Test inequality when any field differs."""
        patch1 = FilePatchInfo(filename="test.py", num_plus_lines=1, num_minus_lines=1)

        patch2 = FilePatchInfo(filename="test.py", num_plus_lines=5, num_minus_lines=0)

        assert patch1 != patch2


class TestFilePatchInfoEdgeCases:
    """Test edge cases and boundary conditions for FilePatchInfo."""

    def test_very_long_filename(self):
        """Test FilePatchInfo with very long filename."""
        long_filename = "a" * 1000 + ".py"

        patch = FilePatchInfo(filename=long_filename)

        assert patch.filename == long_filename

    def test_special_characters_in_filename(self):
        """Test FilePatchInfo with special characters in filename."""
        special_filenames = [
            "src/test-file.py",
            "src/test_file.py",
            "src/test.file.py",
            "src/test (1).py",
        ]

        for filename in special_filenames:
            patch = FilePatchInfo(filename=filename)
            assert patch.filename == filename

    def test_binary_file_detection_by_extension(self):
        """Test binary file detection for various extensions."""
        binary_files = [
            "image.jpg",
            "image.png",
            "image.gif",
            "document.pdf",
            "archive.zip",
            "music.mp3",
            "video.mp4",
            "executable.exe",
        ]

        for filename in binary_files:
            patch = FilePatchInfo(filename=filename)
            assert patch.is_binary is True, f"{filename} should be detected as binary"

    def test_large_line_counts(self):
        """Test FilePatchInfo with large line counts."""
        patch = FilePatchInfo(
            filename="large.py", num_plus_lines=99999, num_minus_lines=99999
        )

        assert patch.num_plus_lines == 99999
        assert patch.num_minus_lines == 99999
        assert patch.total_changes == 199998


class TestFilePatchInfoIntegration:
    """Integration tests for FilePatchInfo with related functionality."""

    def test_file_patch_info_full_workflow(self):
        """Test complete FilePatchInfo usage workflow."""
        # Create a file patch
        patch = FilePatchInfo(
            filename="src/auth.py",
            base_file="def login():\n    pass\n",
            head_file="def login():\n    # TODO: implement\n    pass\n",
            patch="@@ -1,2 +1,3 @@\n def login():\n+    # TODO: implement\n     pass\n",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=1,
            num_minus_lines=0,
            language="Python",
        )

        # Get summary
        summary = patch.get_summary()
        assert summary["filename"] == "src/auth.py"
        assert summary["language"] == "Python"

        # Calculate priority (should be high due to 'auth')
        priority = patch.calculate_review_priority()
        assert priority == "high"

        # Detect code smells
        smells = patch.detect_code_smells()
        assert "Contains TODO comments" in smells

        # Validate
        errors = patch.validate()
        assert errors == []

    def test_review_priority_calculation_order(self):
        """Test that review priority checks patterns in correct order."""
        # Security file should be high priority even if it's a test
        patch = FilePatchInfo(filename="security/test_auth.py")

        priority = patch.calculate_review_priority()
        # Security pattern comes first, so it should be high
        assert priority == "high"

    def test_statistics_consistency(self):
        """Test that statistics remain consistent."""
        patch = FilePatchInfo(
            filename="test.py",
            base_file="line1\nline2\nline3\nline4\nline5\n",
            num_plus_lines=3,
            num_minus_lines=2,
        )

        summary = patch.get_summary()

        # Verify consistency
        assert summary["total_changes"] == patch.total_changes
        assert summary["additions"] == patch.num_plus_lines
        assert summary["deletions"] == patch.num_minus_lines
        assert summary["change_percentage"] == round(patch.change_percentage, 2)
