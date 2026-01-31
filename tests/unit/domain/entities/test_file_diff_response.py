"""Unit tests for FileDiffResponse entity.

Tests FileDiffResponse Pydantic model which represents individual file change
for structured PR diff response.
"""

from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats


class TestFileStatsCreation:
    """Test suite for FileStats creation and validation."""

    def test_file_stats_creation_with_all_fields(self):
        """Test creating FileStats with all fields."""
        stats = FileStats(additions=100, deletions=25)

        assert stats.additions == 100
        assert stats.deletions == 25

    def test_file_stats_creation_with_zero_values(self):
        """Test creating FileStats with zero values."""
        stats = FileStats(additions=0, deletions=0)

        assert stats.additions == 0
        assert stats.deletions == 0

    def test_file_stats_serialization(self):
        """Test FileStats can be serialized."""
        stats = FileStats(additions=50, deletions=10)

        data = stats.model_dump()

        assert data == {"additions": 50, "deletions": 10}


class TestFileDiffResponseCreation:
    """Test suite for FileDiffResponse creation and validation."""

    def test_file_diff_response_creation_minimal(self):
        """Test creating FileDiffResponse with minimal required fields."""
        file_data = {
            "path": "src/test.ts",
            "status": "added",
            "stats": {"additions": 50, "deletions": 10},
            "diff": "@@ -0,0 +1,50 @@\n+new code\n",
        }

        response = FileDiffResponse(**file_data)

        assert response.path == "src/test.ts"
        assert response.status == EDIT_TYPE.ADDED
        assert response.stats.additions == 50
        assert response.stats.deletions == 10
        assert response.diff == "@@ -0,0 +1,50 @@\n+new code\n"

    def test_file_diff_response_creation_with_enum(self):
        """Test creating FileDiffResponse with EDIT_TYPE enum."""
        response = FileDiffResponse(
            path="src/service.py",
            status=EDIT_TYPE.MODIFIED,
            stats=FileStats(additions=25, deletions=15),
            diff="@@ -1,3 +1,8 @@\n-old\n+new\n",
        )

        assert response.path == "src/service.py"
        assert response.status == EDIT_TYPE.MODIFIED
        assert response.stats.additions == 25
        assert response.stats.deletions == 15

    def test_file_diff_response_all_edit_types(self):
        """Test FileDiffResponse with all edit type values."""
        edit_types = [
            EDIT_TYPE.ADDED,
            EDIT_TYPE.MODIFIED,
            EDIT_TYPE.DELETED,
            EDIT_TYPE.RENAMED,
            EDIT_TYPE.UNKNOWN,
        ]

        for edit_type in edit_types:
            response = FileDiffResponse(
                path="test.txt",
                status=edit_type,
                stats=FileStats(additions=0, deletions=0),
                diff="",
            )
            assert response.status == edit_type


class TestFileDiffResponseSerialization:
    """Test suite for FileDiffResponse serialization."""

    def test_model_dump(self):
        """Test Pydantic model_dump serialization."""
        response = FileDiffResponse(
            path="src/file.ts",
            status=EDIT_TYPE.MODIFIED,
            stats=FileStats(additions=10, deletions=5),
            diff="@@ -1,1 +1,1 @@\n-old\n+new",
        )

        data = response.model_dump()

        assert data["path"] == "src/file.ts"
        assert data["status"] == "modified"
        assert data["stats"] == {"additions": 10, "deletions": 5}
        assert data["diff"] == "@@ -1,1 +1,1 @@\n-old\n+new"

    def test_model_dump_json(self):
        """Test Pydantic model_dump_json serialization."""
        response = FileDiffResponse(
            path="test.py",
            status=EDIT_TYPE.ADDED,
            stats=FileStats(additions=100, deletions=0),
            diff="@@ -0,0 +1,100 @@\n+content",
        )

        json_string = response.model_dump_json()

        assert '"path":"test.py"' in json_string
        assert '"status":"added"' in json_string
        assert '"additions":100' in json_string
        assert '"deletions":0' in json_string

    def test_model_validate(self):
        """Test Pydantic model_validate deserialization."""
        data = {
            "path": "src/component.ts",
            "status": EDIT_TYPE.DELETED,
            "stats": {"additions": 0, "deletions": 50},
            "diff": "@@ -1,50 +1,0 @@\n-removed lines",
        }

        response = FileDiffResponse.model_validate(data)

        assert response.path == "src/component.ts"
        assert response.status == EDIT_TYPE.DELETED
        assert response.stats.additions == 0
        assert response.stats.deletions == 50

    def test_round_trip_serialization(self):
        """Test serialization and deserialization round trip."""
        original = FileDiffResponse(
            path="test.ts",
            status=EDIT_TYPE.ADDED,
            stats=FileStats(additions=75, deletions=10),
            diff="test diff",
        )

        # Serialize
        json_data = original.model_dump_json()

        # Deserialize
        restored = FileDiffResponse.model_validate_json(json_data)

        # Verify equality
        assert restored.path == original.path
        assert restored.status == original.status
        assert restored.stats.additions == original.stats.additions
        assert restored.stats.deletions == original.stats.deletions
        assert restored.diff == original.diff


class TestFileDiffResponseEdgeCases:
    """Test edge cases and boundary conditions for FileDiffResponse."""

    def test_empty_diff(self):
        """Test FileDiffResponse with empty diff."""
        response = FileDiffResponse(
            path="empty.txt",
            status=EDIT_TYPE.ADDED,
            stats=FileStats(additions=0, deletions=0),
            diff="",
        )

        assert response.diff == ""

    def test_large_stats(self):
        """Test FileDiffResponse with large stats values."""
        response = FileDiffResponse(
            path="large.py",
            status=EDIT_TYPE.MODIFIED,
            stats=FileStats(additions=10000, deletions=5000),
            diff="diff content",
        )

        assert response.stats.additions == 10000
        assert response.stats.deletions == 5000

    def test_special_characters_in_path(self):
        """Test FileDiffResponse with special characters in path."""
        response = FileDiffResponse(
            path="path/with spaces/and-dashes/file.ts",
            status=EDIT_TYPE.MODIFIED,
            stats=FileStats(additions=1, deletions=1),
            diff="diff",
        )

        assert response.path == "path/with spaces/and-dashes/file.ts"
