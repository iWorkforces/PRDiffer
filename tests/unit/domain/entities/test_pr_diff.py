"""Unit tests for PRDiff entity.

Tests the PRDiff Pydantic model which represents pull request information
with diff content only (simplified version).
"""

from prdiffer.domain.entities.pr_diff import PRDiff


class TestPRDiffCreation:
    """Test suite for PRDiff creation and validation."""

    def test_pr_diff_creation_minimal(self):
        """Test creating a PRDiff with minimal required fields."""
        pr_diff = PRDiff()

        assert pr_diff.diff_content == ""

    def test_pr_diff_creation_with_content(self):
        """Test creating a PRDiff with diff content."""
        pr_diff = PRDiff(
            diff_content="@@ -1,5 +1,10 @@\n+new line\n old line\n",
        )

        assert pr_diff.diff_content == "@@ -1,5 +1,10 @@\n+new line\n old line\n"


class TestPRDiffProperties:
    """Test suite for PRDiff property methods."""

    def test_has_content_true(self):
        """Test has_content returns True when there is diff content."""
        pr_diff = PRDiff(
            diff_content="@@ -1,3 +1,5 @@\n+new line\n old line\n",
        )

        assert pr_diff.has_content is True

    def test_has_content_false_empty_string(self):
        """Test has_content returns False for empty string."""
        pr_diff = PRDiff(diff_content="")

        assert pr_diff.has_content is False

    def test_has_content_false_whitespace_only(self):
        """Test has_content returns False for whitespace-only content."""
        pr_diff = PRDiff(diff_content="   \n\t  \n  ")

        assert pr_diff.has_content is False

    def test_has_content_false_none_default(self):
        """Test has_content returns False when using default."""
        pr_diff = PRDiff()

        assert pr_diff.has_content is False


class TestPRDiffEdgeCases:
    """Test edge cases and boundary conditions for PRDiff."""

    def test_diff_content_with_newlines(self):
        """Test has_content with various newline patterns."""
        pr_diff = PRDiff(diff_content="\n\n")

        assert pr_diff.has_content is False

        pr_diff = PRDiff(diff_content="\n\ncode\n")

        assert pr_diff.has_content is True


class TestPRDiffSerialization:
    """Test Pydantic serialization capabilities of PRDiff."""

    def test_model_dump(self):
        """Test Pydantic model_dump serialization."""
        pr_diff = PRDiff(diff_content="diff")

        data = pr_diff.model_dump()

        assert data["diff_content"] == "diff"

    def test_model_dump_json(self):
        """Test Pydantic model_dump_json serialization."""
        pr_diff = PRDiff(diff_content="diff")

        json_string = pr_diff.model_dump_json()

        assert "diff_content" in json_string
        assert '"diff_content":"diff"' in json_string

    def test_model_validate(self):
        """Test Pydantic model_validate deserialization."""
        data = {"diff_content": "diff"}

        pr_diff = PRDiff.model_validate(data)

        assert pr_diff.diff_content == "diff"

    def test_model_validate_json(self):
        """Test Pydantic model_validate_json deserialization."""
        json_string = '{"diff_content":"diff"}'

        pr_diff = PRDiff.model_validate_json(json_string)

        assert pr_diff.diff_content == "diff"

    def test_round_trip_serialization(self):
        """Test serialization and deserialization round trip."""
        original = PRDiff(diff_content="sample diff")

        # Serialize
        json_data = original.model_dump_json()

        # Deserialize
        restored = PRDiff.model_validate_json(json_data)

        # Verify equality
        assert restored.diff_content == original.diff_content


class TestPRDiffImmutability:
    """Test immutability characteristics of PRDiff."""

    def test_immutability_with_frozen(self):
        """Test that PRDiff instances are mutable (frozen=False by default)."""
        pr_diff = PRDiff(diff_content="original diff")

        # Pydantic models are mutable by default unless frozen=True
        # This test verifies the current behavior (mutable)
        pr_diff.diff_content = "modified diff"
        assert pr_diff.diff_content == "modified diff"

    def test_model_copy(self):
        """Test Pydantic model_copy creates independent copy."""
        original = PRDiff(diff_content="diff")

        copy = original.model_copy()

        # Verify copy has same values
        assert copy.diff_content == original.diff_content

        # Verify independence (modify copy, original unchanged)
        copy.diff_content = "modified"
        assert original.diff_content == "diff"
        assert copy.diff_content == "modified"

    def test_model_copy_with_updates(self):
        """Test model_copy with update parameter."""
        original = PRDiff(diff_content="original")

        copy = original.model_copy(update={"diff_content": "modified"})

        assert original.diff_content == "original"
        assert copy.diff_content == "modified"
