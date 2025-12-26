"""Unit tests for PRDiff entity.

Tests the PRDiff Pydantic model which represents pull request information
with diff content, commit messages, statistics, and metadata.
"""

from ccpragents.domain.entities.pr_diff import PRDiff


class TestPRDiffCreation:
    """Test suite for PRDiff creation and validation."""

    def test_pr_diff_creation_minimal(self):
        """Test creating a PRDiff with minimal required fields."""
        pr_diff = PRDiff()

        assert pr_diff.diff_content == ""
        assert pr_diff.commit_messages is None
        assert pr_diff.files_changed == 0
        assert pr_diff.total_additions == 0
        assert pr_diff.total_deletions == 0
        assert pr_diff.generation_metadata is None
        assert pr_diff.file_summaries is None

    def test_pr_diff_creation_with_content(self):
        """Test creating a PRDiff with diff content and commit messages."""
        pr_diff = PRDiff(
            diff_content="@@ -1,5 +1,10 @@\n+new line\n old line\n",
            commit_messages="1. Initial commit\n2. Add feature",
        )

        assert pr_diff.diff_content == "@@ -1,5 +1,10 @@\n+new line\n old line\n"
        assert pr_diff.commit_messages == "1. Initial commit\n2. Add feature"

    def test_pr_diff_creation_with_statistics(self):
        """Test creating a PRDiff with file statistics."""
        pr_diff = PRDiff(
            files_changed=5,
            total_additions=100,
            total_deletions=50,
        )

        assert pr_diff.files_changed == 5
        assert pr_diff.total_additions == 100
        assert pr_diff.total_deletions == 50

    def test_pr_diff_creation_with_metadata(self):
        """Test creating a PRDiff with generation metadata."""
        metadata = {
            "cache_status": "hit",
            "generation_time_ms": 1500,
            "api_calls": 3,
        }

        pr_diff = PRDiff(
            generation_metadata=metadata,
        )

        assert pr_diff.generation_metadata == metadata
        assert pr_diff.generation_metadata["cache_status"] == "hit"

    def test_pr_diff_creation_with_file_summaries(self):
        """Test creating a PRDiff with file summaries."""
        file_summaries = [
            {
                "filename": "src/main.py",
                "additions": 10,
                "deletions": 5,
                "edit_type": "modified",
            },
            {
                "filename": "src/new_file.py",
                "additions": 20,
                "deletions": 0,
                "edit_type": "added",
            },
        ]

        pr_diff = PRDiff(
            file_summaries=file_summaries,
        )

        assert pr_diff.file_summaries == file_summaries
        assert len(pr_diff.file_summaries) == 2

    def test_pr_diff_creation_complete(self):
        """Test creating a PRDiff with all fields populated."""
        metadata = {"generation_time_ms": 1200}
        file_summaries = [{"filename": "test.py", "additions": 5, "deletions": 3}]

        pr_diff = PRDiff(
            diff_content="diff content",
            commit_messages="commit messages",
            files_changed=10,
            total_additions=50,
            total_deletions=25,
            generation_metadata=metadata,
            file_summaries=file_summaries,
        )

        assert pr_diff.diff_content == "diff content"
        assert pr_diff.commit_messages == "commit messages"
        assert pr_diff.files_changed == 10
        assert pr_diff.total_additions == 50
        assert pr_diff.total_deletions == 25
        assert pr_diff.generation_metadata == metadata
        assert pr_diff.file_summaries == file_summaries

    def test_pr_diff_negative_statistics_accepted(self):
        """Test that negative statistics are accepted (no validation enforced).

        Note: The current PRDiff model does not enforce non-negative validation
        for statistics fields. This test documents the current behavior.
        """
        pr_diff = PRDiff(
            files_changed=-1,
            total_additions=-10,
            total_deletions=-5,
        )

        # Current implementation accepts negative values
        assert pr_diff.files_changed == -1
        assert pr_diff.total_additions == -10
        assert pr_diff.total_deletions == -5
        assert pr_diff.total_changes == -15  # -10 + -5


class TestPRDiffProperties:
    """Test suite for PRDiff property methods."""

    def test_total_changes_property(self):
        """Test the total_changes property calculation."""
        pr_diff = PRDiff(
            total_additions=100,
            total_deletions=50,
        )

        assert pr_diff.total_changes == 150

    def test_total_changes_zero(self):
        """Test total_changes when no additions or deletions."""
        pr_diff = PRDiff()

        assert pr_diff.total_changes == 0

    def test_total_changes_additions_only(self):
        """Test total_changes with only additions."""
        pr_diff = PRDiff(
            total_additions=75,
            total_deletions=0,
        )

        assert pr_diff.total_changes == 75

    def test_total_changes_deletions_only(self):
        """Test total_changes with only deletions."""
        pr_diff = PRDiff(
            total_additions=0,
            total_deletions=30,
        )

        assert pr_diff.total_changes == 30

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


class TestPRDiffStatistics:
    """Test suite for PRDiff.get_statistics() method."""

    def test_get_statistics_basic(self):
        """Test get_statistics returns all expected fields."""
        pr_diff = PRDiff(
            files_changed=5,
            total_additions=100,
            total_deletions=50,
            diff_content="some diff content",
            commit_messages="commit1\ncommit2\ncommit3",
        )

        stats = pr_diff.get_statistics()

        assert "files_changed" in stats
        assert "total_additions" in stats
        assert "total_deletions" in stats
        assert "total_changes" in stats
        assert "has_content" in stats
        assert "commit_count" in stats

    def test_get_statistics_values(self):
        """Test get_statistics returns correct values."""
        pr_diff = PRDiff(
            files_changed=10,
            total_additions=200,
            total_deletions=75,
            diff_content="diff content",
            commit_messages="commit1\ncommit2\ncommit3",
        )

        stats = pr_diff.get_statistics()

        assert stats["files_changed"] == 10
        assert stats["total_additions"] == 200
        assert stats["total_deletions"] == 75
        assert stats["total_changes"] == 275  # 200 + 75
        assert stats["has_content"] is True
        assert stats["commit_count"] == 3

    def test_get_statistics_no_content(self):
        """Test get_statistics when there is no diff content."""
        pr_diff = PRDiff(
            diff_content="",
            commit_messages=None,
        )

        stats = pr_diff.get_statistics()

        assert stats["has_content"] is False
        assert stats["commit_count"] == 0

    def test_get_statistics_empty_commit_messages(self):
        """Test get_statistics with empty commit messages."""
        pr_diff = PRDiff(commit_messages="")

        stats = pr_diff.get_statistics()

        assert stats["commit_count"] == 0

    def test_get_statistics_single_commit(self):
        """Test get_statistics with single commit message."""
        pr_diff = PRDiff(commit_messages="Initial commit")

        stats = pr_diff.get_statistics()

        assert stats["commit_count"] == 1

    def test_get_statistics_multiline_commits(self):
        """Test get_statistics with multiline commit messages."""
        pr_diff = PRDiff(
            commit_messages="1. First commit\n2. Second commit\n3. Third commit\n4. Fourth commit"
        )

        stats = pr_diff.get_statistics()

        assert stats["commit_count"] == 4


class TestPRDiffResponseEnvelope:
    """Test suite for PRDiff.get_response_envelope() method."""

    def test_get_response_envelope_structure(self):
        """Test get_response_envelope returns expected structure."""
        pr_diff = PRDiff(
            diff_content="diff content",
            commit_messages="commit messages",
        )

        envelope = pr_diff.get_response_envelope()

        assert "content" in envelope
        assert "statistics" in envelope
        assert "metadata" in envelope
        assert "file_summaries" in envelope

    def test_get_response_envelope_content(self):
        """Test get_response_envelope content section."""
        pr_diff = PRDiff(
            diff_content="sample diff",
            commit_messages="sample commits",
        )

        envelope = pr_diff.get_response_envelope()

        assert envelope["content"]["diff"] == "sample diff"
        assert envelope["content"]["commit_messages"] == "sample commits"

    def test_get_response_envelope_statistics(self):
        """Test get_response_envelope statistics section."""
        pr_diff = PRDiff(
            files_changed=5,
            total_additions=100,
            total_deletions=50,
            diff_content="diff",
            commit_messages="commits",
        )

        envelope = pr_diff.get_response_envelope()

        assert envelope["statistics"]["files_changed"] == 5
        assert envelope["statistics"]["total_additions"] == 100
        assert envelope["statistics"]["total_deletions"] == 50
        assert envelope["statistics"]["total_changes"] == 150

    def test_get_response_envelope_metadata(self):
        """Test get_response_envelope metadata section."""
        metadata = {"cache": "hit", "time_ms": 1000}
        pr_diff = PRDiff(generation_metadata=metadata)

        envelope = pr_diff.get_response_envelope()

        assert envelope["metadata"] == metadata
        assert envelope["metadata"]["cache"] == "hit"
        assert envelope["metadata"]["time_ms"] == 1000

    def test_get_response_envelope_empty_metadata(self):
        """Test get_response_envelope with no metadata."""
        pr_diff = PRDiff()

        envelope = pr_diff.get_response_envelope()

        assert envelope["metadata"] == {}

    def test_get_response_envelope_file_summaries(self):
        """Test get_response_envelope file_summaries section."""
        file_summaries = [
            {"filename": "file1.py", "additions": 10},
            {"filename": "file2.py", "additions": 20},
        ]
        pr_diff = PRDiff(file_summaries=file_summaries)

        envelope = pr_diff.get_response_envelope()

        assert envelope["file_summaries"] == file_summaries
        assert len(envelope["file_summaries"]) == 2

    def test_get_response_envelope_empty_file_summaries(self):
        """Test get_response_envelope with no file summaries."""
        pr_diff = PRDiff()

        envelope = pr_diff.get_response_envelope()

        assert envelope["file_summaries"] == []

    def test_get_response_envelope_complete(self):
        """Test get_response_envelope with all data populated."""
        metadata = {"generation_time_ms": 1500}
        file_summaries = [{"filename": "test.py", "additions": 5, "deletions": 3}]

        pr_diff = PRDiff(
            diff_content="diff",
            commit_messages="commits",
            files_changed=5,
            total_additions=50,
            total_deletions=25,
            generation_metadata=metadata,
            file_summaries=file_summaries,
        )

        envelope = pr_diff.get_response_envelope()

        # Verify all sections
        assert envelope["content"]["diff"] == "diff"
        assert envelope["content"]["commit_messages"] == "commits"
        assert envelope["statistics"]["files_changed"] == 5
        assert envelope["statistics"]["total_additions"] == 50
        assert envelope["statistics"]["total_deletions"] == 25
        assert envelope["statistics"]["total_changes"] == 75
        assert envelope["metadata"] == metadata
        assert envelope["file_summaries"] == file_summaries


class TestPRDiffEdgeCases:
    """Test edge cases and boundary conditions for PRDiff."""

    def test_large_statistics_values(self):
        """Test PRDiff with very large statistic values."""
        pr_diff = PRDiff(
            files_changed=1000000,
            total_additions=10000000,
            total_deletions=5000000,
        )

        assert pr_diff.files_changed == 1000000
        assert pr_diff.total_additions == 10000000
        assert pr_diff.total_deletions == 5000000
        assert pr_diff.total_changes == 15000000

    def test_empty_diff_content_with_commits(self):
        """Test PRDiff with empty diff but has commit messages."""
        pr_diff = PRDiff(
            diff_content="",
            commit_messages="commit1\ncommit2",
        )

        assert pr_diff.has_content is False
        assert pr_diff.commit_messages == "commit1\ncommit2"

    def test_diff_content_with_newlines(self):
        """Test has_content with various newline patterns."""
        pr_diff = PRDiff(diff_content="\n\n")

        assert pr_diff.has_content is False

        pr_diff = PRDiff(diff_content="\n\ncode\n")

        assert pr_diff.has_content is True

    def test_commit_messages_with_trailing_newline(self):
        """Test commit_count with trailing newline.

        Note: Python's split("\n") creates an empty string for trailing newlines,
        so "commit1\ncommit2\n" splits into 3 elements: ["commit1", "commit2", ""]
        """
        pr_diff = PRDiff(commit_messages="commit1\ncommit2\n")

        stats = pr_diff.get_statistics()
        # Trailing newline adds an empty entry to the split result
        assert stats["commit_count"] == 3

    def test_complex_generation_metadata(self):
        """Test PRDiff with complex nested metadata."""
        metadata = {
            "generation_time_ms": 1500,
            "api_calls": [
                {"endpoint": "/files", "duration_ms": 200},
                {"endpoint": "/commits", "duration_ms": 100},
            ],
            "cache_info": {
                "hits": 3,
                "misses": 1,
                "hit_rate": 0.75,
            },
        }

        pr_diff = PRDiff(generation_metadata=metadata)

        assert pr_diff.generation_metadata == metadata
        assert pr_diff.generation_metadata["cache_info"]["hit_rate"] == 0.75

    def test_file_summaries_with_extended_fields(self):
        """Test file_summaries with extended information."""
        file_summaries = [
            {
                "filename": "src/main.py",
                "additions": 10,
                "deletions": 5,
                "edit_type": "modified",
                "language": "Python",
                "complexity_delta": 5,
                "functions_changed": ["main", "process"],
            },
        ]

        pr_diff = PRDiff(file_summaries=file_summaries)

        assert len(pr_diff.file_summaries) == 1
        assert pr_diff.file_summaries[0]["language"] == "Python"
        assert "main" in pr_diff.file_summaries[0]["functions_changed"]


class TestPRDiffSerialization:
    """Test Pydantic serialization capabilities of PRDiff."""

    def test_model_dump(self):
        """Test Pydantic model_dump serialization."""
        pr_diff = PRDiff(
            diff_content="diff",
            commit_messages="commits",
            files_changed=5,
            total_additions=10,
            total_deletions=5,
        )

        data = pr_diff.model_dump()

        assert data["diff_content"] == "diff"
        assert data["commit_messages"] == "commits"
        assert data["files_changed"] == 5
        assert data["total_additions"] == 10
        assert data["total_deletions"] == 5

    def test_model_dump_json(self):
        """Test Pydantic model_dump_json serialization."""
        pr_diff = PRDiff(
            diff_content="diff",
            commit_messages="commits",
        )

        json_string = pr_diff.model_dump_json()

        assert "diff_content" in json_string
        assert "commit_messages" in json_string
        assert '"diff_content":"diff"' in json_string

    def test_model_validate(self):
        """Test Pydantic model_validate deserialization."""
        data = {
            "diff_content": "diff",
            "commit_messages": "commits",
            "files_changed": 10,
            "total_additions": 50,
            "total_deletions": 25,
        }

        pr_diff = PRDiff.model_validate(data)

        assert pr_diff.diff_content == "diff"
        assert pr_diff.commit_messages == "commits"
        assert pr_diff.files_changed == 10
        assert pr_diff.total_additions == 50
        assert pr_diff.total_deletions == 25

    def test_model_validate_json(self):
        """Test Pydantic model_validate_json deserialization."""
        json_string = (
            '{"diff_content":"diff","commit_messages":"commits","files_changed":5}'
        )

        pr_diff = PRDiff.model_validate_json(json_string)

        assert pr_diff.diff_content == "diff"
        assert pr_diff.commit_messages == "commits"
        assert pr_diff.files_changed == 5

    def test_round_trip_serialization(self):
        """Test serialization and deserialization round trip."""
        original = PRDiff(
            diff_content="sample diff",
            commit_messages="sample commits",
            files_changed=15,
            total_additions=100,
            total_deletions=50,
            generation_metadata={"time": 1000},
            file_summaries=[{"filename": "test.py"}],
        )

        # Serialize
        json_data = original.model_dump_json()

        # Deserialize
        restored = PRDiff.model_validate_json(json_data)

        # Verify equality
        assert restored.diff_content == original.diff_content
        assert restored.commit_messages == original.commit_messages
        assert restored.files_changed == original.files_changed
        assert restored.total_additions == original.total_additions
        assert restored.total_deletions == original.total_deletions


class TestPRDiffImmutability:
    """Test immutability characteristics of PRDiff."""

    def test_immutability_with_frozen(self):
        """Test that PRDiff instances are immutable when frozen."""
        pr_diff = PRDiff(
            diff_content="original diff",
            files_changed=5,
        )

        # Pydantic models are mutable by default unless frozen=True
        # This test verifies the current behavior (mutable)
        pr_diff.diff_content = "modified diff"
        assert pr_diff.diff_content == "modified diff"

    def test_model_copy(self):
        """Test Pydantic model_copy creates independent copy."""
        original = PRDiff(
            diff_content="diff",
            files_changed=5,
        )

        copy = original.model_copy()

        # Verify copy has same values
        assert copy.diff_content == original.diff_content
        assert copy.files_changed == original.files_changed

        # Verify independence (modify copy, original unchanged)
        copy.diff_content = "modified"
        assert original.diff_content == "diff"
        assert copy.diff_content == "modified"

    def test_model_copy_with_updates(self):
        """Test model_copy with update parameter."""
        original = PRDiff(
            diff_content="original",
            files_changed=5,
        )

        copy = original.model_copy(update={"files_changed": 10})

        assert original.files_changed == 5
        assert copy.files_changed == 10
        assert copy.diff_content == "original"


class TestPRDiffIntegration:
    """Integration tests for PRDiff with related components."""

    def test_pr_diff_statistics_consistency(self):
        """Test that statistics remain consistent across operations."""
        pr_diff = PRDiff(
            files_changed=10,
            total_additions=100,
            total_deletions=50,
            diff_content="diff content",
            commit_messages="commit1\ncommit2\ncommit3",
        )

        # Get statistics multiple times
        stats1 = pr_diff.get_statistics()
        stats2 = pr_diff.get_statistics()

        # Verify consistency
        assert stats1 == stats2
        assert stats1["total_changes"] == stats2["total_changes"]

    def test_response_envelope_matches_statistics(self):
        """Test that response envelope statistics match get_statistics."""
        pr_diff = PRDiff(
            files_changed=7,
            total_additions=70,
            total_deletions=35,
            diff_content="diff",
            commit_messages="commits",
        )

        envelope = pr_diff.get_response_envelope()
        stats = pr_diff.get_statistics()

        # Verify statistics match
        assert envelope["statistics"]["files_changed"] == stats["files_changed"]
        assert envelope["statistics"]["total_additions"] == stats["total_additions"]
        assert envelope["statistics"]["total_deletions"] == stats["total_deletions"]
        assert envelope["statistics"]["total_changes"] == stats["total_changes"]
        assert envelope["statistics"]["has_content"] == stats["has_content"]
        assert envelope["statistics"]["commit_count"] == stats["commit_count"]
