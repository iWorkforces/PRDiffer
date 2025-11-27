"""
Tests for Phase 3 Improvements: API Enhancement

This module contains unit tests for Phase 3 improvements including:
- Extended FilePatchInfo data model
- Extended PRDiff data model
- Structured error codes
- Error handling utilities
"""


# =============================================================================
# Phase 3.1: Extended FilePatchInfo Tests
# =============================================================================


class TestFilePatchInfoExtensions:
    """Tests for extended FilePatchInfo data model."""

    def test_new_fields_have_defaults(self):
        """Test that new fields have sensible defaults."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        patch = FilePatchInfo(
            filename="test.py",
            base_file="old",
            head_file="new",
            patch="@@ diff @@",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=1,
            num_minus_lines=1,
        )

        # New Phase 3 fields should have defaults
        assert patch.diff_metadata is None
        assert patch.code_smell_indicators is None
        assert patch.suggested_review_priority == "normal"

    def test_calculate_review_priority_high_for_security_files(self):
        """Test high priority for security-sensitive files."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        security_files = [
            "auth.py",
            "security/config.py",
            "password_manager.py",
            "token_handler.py",
            ".env.example",
        ]

        for filename in security_files:
            patch = FilePatchInfo(
                filename=filename,
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=5,
                num_minus_lines=3,
            )
            assert patch.calculate_review_priority() == "high", (
                f"Expected high for {filename}"
            )

    def test_calculate_review_priority_high_for_large_changes(self):
        """Test high priority for large change sets."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        patch = FilePatchInfo(
            filename="regular.py",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=80,
            num_minus_lines=50,  # 130 total changes > 100
        )

        assert patch.calculate_review_priority() == "high"

    def test_calculate_review_priority_low_for_docs(self):
        """Test low priority for documentation files."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        doc_files = ["README.md", "docs/api.md", "CHANGELOG.txt", "LICENSE"]
        # Provide enough base_file content to keep change_percentage < 50%
        base_content = "\n".join([f"line {i}" for i in range(100)])

        for filename in doc_files:
            patch = FilePatchInfo(
                filename=filename,
                base_file=base_content,
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=5,
                num_minus_lines=3,
            )
            assert patch.calculate_review_priority() == "low", (
                f"Expected low for {filename}"
            )

    def test_calculate_review_priority_low_for_tests(self):
        """Test low priority for test files."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        test_files = ["test_main.py", "tests/unit/test_api.py", "spec/test_helper.js"]
        # Provide enough base_file content to keep change_percentage < 50%
        base_content = "\n".join([f"line {i}" for i in range(100)])

        for filename in test_files:
            patch = FilePatchInfo(
                filename=filename,
                base_file=base_content,
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=10,
                num_minus_lines=5,
            )
            assert patch.calculate_review_priority() == "low", (
                f"Expected low for {filename}"
            )

    def test_calculate_review_priority_normal_for_regular_files(self):
        """Test normal priority for regular source files."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        # Provide enough base_file content to keep change_percentage < 50%
        base_content = "\n".join([f"line {i}" for i in range(100)])

        patch = FilePatchInfo(
            filename="src/utils.py",
            base_file=base_content,
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=10,
            num_minus_lines=5,
        )

        assert patch.calculate_review_priority() == "normal"

    def test_detect_code_smells_todo(self):
        """Test detection of TODO comments."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        patch = FilePatchInfo(
            filename="test.py",
            patch="+# TODO: fix this later\n+def broken():\n+    pass",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=3,
            num_minus_lines=0,
        )

        smells = patch.detect_code_smells()
        assert any("TODO" in s for s in smells)

    def test_detect_code_smells_fixme(self):
        """Test detection of FIXME comments."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        patch = FilePatchInfo(
            filename="test.py",
            patch="+# FIXME: this is broken\n+return None",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=2,
            num_minus_lines=0,
        )

        smells = patch.detect_code_smells()
        assert any("FIXME" in s for s in smells)

    def test_detect_code_smells_debug_statements(self):
        """Test detection of debug statements."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        patch = FilePatchInfo(
            filename="test.py",
            patch="+print('debugging')\n+console.log('test')",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=2,
            num_minus_lines=0,
        )

        smells = patch.detect_code_smells()
        assert any("print" in s for s in smells) or any(
            "console.log" in s for s in smells
        )

    def test_detect_code_smells_large_changes(self):
        """Test detection of very large change sets."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        patch = FilePatchInfo(
            filename="test.py",
            patch="@@ -1,500 +1,600 @@",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=600,
            num_minus_lines=0,
        )

        smells = patch.detect_code_smells()
        assert any("large" in s.lower() for s in smells)

    def test_detect_code_smells_empty_patch(self):
        """Test that empty patch returns no smells."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        patch = FilePatchInfo(
            filename="test.py",
            patch="",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=0,
            num_minus_lines=0,
        )

        smells = patch.detect_code_smells()
        assert smells == []

    def test_get_summary_includes_new_fields(self):
        """Test that get_summary includes new Phase 3 fields."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        patch = FilePatchInfo(
            filename="test.py",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=5,
            num_minus_lines=3,
            suggested_review_priority="high",
            code_smell_indicators=["Contains TODO"],
        )

        summary = patch.get_summary()

        assert "review_priority" in summary
        assert "code_smell_indicators" in summary
        assert summary["review_priority"] == "high"
        assert summary["code_smell_indicators"] == ["Contains TODO"]


# =============================================================================
# Phase 3.1: Extended PRDiff Tests
# =============================================================================


class TestPRDiffExtensions:
    """Tests for extended PRDiff data model."""

    def test_new_fields_have_defaults(self):
        """Test that new fields have sensible defaults."""
        from ccpragents.domain.entities.pr_diff import PRDiff

        diff = PRDiff(diff_content="test", commit_messages="message")

        assert diff.files_changed == 0
        assert diff.total_additions == 0
        assert diff.total_deletions == 0
        assert diff.generation_metadata is None
        assert diff.file_summaries is None

    def test_total_changes_property(self):
        """Test total_changes property calculation."""
        from ccpragents.domain.entities.pr_diff import PRDiff

        diff = PRDiff(
            diff_content="test",
            total_additions=50,
            total_deletions=30,
        )

        assert diff.total_changes == 80

    def test_has_content_true(self):
        """Test has_content returns True for non-empty content."""
        from ccpragents.domain.entities.pr_diff import PRDiff

        diff = PRDiff(diff_content="@@ -1,3 +1,3 @@")
        assert diff.has_content is True

    def test_has_content_false_empty(self):
        """Test has_content returns False for empty content."""
        from ccpragents.domain.entities.pr_diff import PRDiff

        diff = PRDiff(diff_content="")
        assert diff.has_content is False

        diff2 = PRDiff(diff_content="   ")
        assert diff2.has_content is False

    def test_get_statistics(self):
        """Test get_statistics method."""
        from ccpragents.domain.entities.pr_diff import PRDiff

        diff = PRDiff(
            diff_content="test diff",
            commit_messages="1. First\n2. Second\n3. Third",
            files_changed=5,
            total_additions=100,
            total_deletions=50,
        )

        stats = diff.get_statistics()

        assert stats["files_changed"] == 5
        assert stats["total_additions"] == 100
        assert stats["total_deletions"] == 50
        assert stats["total_changes"] == 150
        assert stats["has_content"] is True
        assert stats["commit_count"] == 3

    def test_get_response_envelope(self):
        """Test get_response_envelope method."""
        from ccpragents.domain.entities.pr_diff import PRDiff

        diff = PRDiff(
            diff_content="test diff",
            commit_messages="1. First commit",
            files_changed=3,
            total_additions=50,
            total_deletions=20,
            generation_metadata={"cache_hit": True, "generation_time_ms": 150},
            file_summaries=[{"filename": "test.py", "additions": 50, "deletions": 20}],
        )

        envelope = diff.get_response_envelope()

        assert "content" in envelope
        assert "statistics" in envelope
        assert "metadata" in envelope
        assert "file_summaries" in envelope

        assert envelope["content"]["diff"] == "test diff"
        assert envelope["content"]["commit_messages"] == "1. First commit"
        assert envelope["statistics"]["files_changed"] == 3
        assert envelope["metadata"]["cache_hit"] is True
        assert len(envelope["file_summaries"]) == 1


# =============================================================================
# Phase 3.2: Structured Error Codes Tests
# =============================================================================


class TestStructuredErrorCodes:
    """Tests for structured error code system."""

    def test_error_code_string_format(self):
        """Test error code string representation."""
        from ccpragents.domain.errors import E1001_INVALID_URL

        assert str(E1001_INVALID_URL) == "E1001_INVALID_URL"

    def test_error_code_to_dict(self):
        """Test error code conversion to dictionary."""
        from ccpragents.domain.errors import E1001_INVALID_URL

        result = E1001_INVALID_URL.to_dict()

        assert "error_code" in result
        assert "message" in result
        assert "remediation" in result
        assert "category" in result
        assert result["error_code"] == "E1001_INVALID_URL"

    def test_input_validation_errors(self):
        """Test input validation error codes."""
        from ccpragents.domain.errors import (
            E1001_INVALID_URL,
            E1002_INVALID_REPOSITORY,
            E1003_INVALID_PR_NUMBER,
            E1004_SUSPICIOUS_INPUT,
            ErrorCategory,
        )

        errors = [
            E1001_INVALID_URL,
            E1002_INVALID_REPOSITORY,
            E1003_INVALID_PR_NUMBER,
            E1004_SUSPICIOUS_INPUT,
        ]

        for error in errors:
            assert error.category == ErrorCategory.INPUT_VALIDATION
            assert error.code.startswith("E1")

    def test_authentication_errors(self):
        """Test authentication error codes."""
        from ccpragents.domain.errors import (
            E2001_AUTH_REQUIRED,
            E2002_AUTH_FAILED,
            E2003_INSUFFICIENT_PERMISSIONS,
            ErrorCategory,
        )

        errors = [
            E2001_AUTH_REQUIRED,
            E2002_AUTH_FAILED,
            E2003_INSUFFICIENT_PERMISSIONS,
        ]

        for error in errors:
            assert error.category == ErrorCategory.AUTHENTICATION
            assert error.code.startswith("E2")

    def test_rate_limiting_errors(self):
        """Test rate limiting error codes."""
        from ccpragents.domain.errors import (
            E3001_RATE_LIMITED,
            E3002_SECONDARY_RATE_LIMIT,
            ErrorCategory,
        )

        errors = [E3001_RATE_LIMITED, E3002_SECONDARY_RATE_LIMIT]

        for error in errors:
            assert error.category == ErrorCategory.RATE_LIMITING
            assert error.code.startswith("E3")

    def test_not_found_errors(self):
        """Test resource not found error codes."""
        from ccpragents.domain.errors import (
            E4001_REPO_NOT_FOUND,
            E4002_PR_NOT_FOUND,
            E4003_FILE_NOT_FOUND,
            ErrorCategory,
        )

        errors = [E4001_REPO_NOT_FOUND, E4002_PR_NOT_FOUND, E4003_FILE_NOT_FOUND]

        for error in errors:
            assert error.category == ErrorCategory.NOT_FOUND
            assert error.code.startswith("E4")

    def test_internal_errors(self):
        """Test internal server error codes."""
        from ccpragents.domain.errors import (
            E5001_INTERNAL_ERROR,
            E5002_GITHUB_API_ERROR,
            E5003_DIFF_GENERATION_ERROR,
            ErrorCategory,
        )

        errors = [
            E5001_INTERNAL_ERROR,
            E5002_GITHUB_API_ERROR,
            E5003_DIFF_GENERATION_ERROR,
        ]

        for error in errors:
            assert error.category == ErrorCategory.INTERNAL
            assert error.code.startswith("E5")


class TestMCPErrorException:
    """Tests for MCPError exception class."""

    def test_mcp_error_creation(self):
        """Test MCPError exception creation."""
        from ccpragents.domain.errors import MCPError, E1001_INVALID_URL

        error = MCPError(E1001_INVALID_URL)

        assert error.error_code == E1001_INVALID_URL
        assert error.detail is None
        assert error.context == {}

    def test_mcp_error_with_detail(self):
        """Test MCPError with additional detail."""
        from ccpragents.domain.errors import MCPError, E1001_INVALID_URL

        error = MCPError(E1001_INVALID_URL, detail="URL missing protocol")

        assert error.detail == "URL missing protocol"

    def test_mcp_error_with_context(self):
        """Test MCPError with context information."""
        from ccpragents.domain.errors import MCPError, E1001_INVALID_URL

        error = MCPError(E1001_INVALID_URL, context={"provided_url": "invalid://url"})

        assert error.context["provided_url"] == "invalid://url"

    def test_mcp_error_to_dict(self):
        """Test MCPError conversion to dictionary."""
        from ccpragents.domain.errors import MCPError, E1001_INVALID_URL

        error = MCPError(
            E1001_INVALID_URL, detail="Missing protocol", context={"url": "test"}
        )

        result = error.to_dict()

        assert "error_code" in result
        assert "message" in result
        assert "detail" in result
        assert "context" in result
        assert result["detail"] == "Missing protocol"

    def test_category_specific_exceptions(self):
        """Test category-specific exception classes."""
        from ccpragents.domain.errors import (
            InputValidationError,
            AuthenticationError,
            RateLimitError,
            ResourceNotFoundError,
            InternalServerError,
            MCPError,
            E1001_INVALID_URL,
            E2001_AUTH_REQUIRED,
            E3001_RATE_LIMITED,
            E4001_REPO_NOT_FOUND,
            E5001_INTERNAL_ERROR,
        )

        # All should be subclasses of MCPError
        assert issubclass(InputValidationError, MCPError)
        assert issubclass(AuthenticationError, MCPError)
        assert issubclass(RateLimitError, MCPError)
        assert issubclass(ResourceNotFoundError, MCPError)
        assert issubclass(InternalServerError, MCPError)

        # Create instances
        errors = [
            InputValidationError(E1001_INVALID_URL),
            AuthenticationError(E2001_AUTH_REQUIRED),
            RateLimitError(E3001_RATE_LIMITED),
            ResourceNotFoundError(E4001_REPO_NOT_FOUND),
            InternalServerError(E5001_INTERNAL_ERROR),
        ]

        for error in errors:
            assert isinstance(error, MCPError)


class TestErrorHandlingUtilities:
    """Tests for error handling utility functions."""

    def test_get_error_for_exception_known_types(self):
        """Test mapping known exception types to error codes."""
        from ccpragents.domain.errors import (
            get_error_for_exception,
            E1001_INVALID_URL,
            E5004_TIMEOUT_ERROR,
        )

        # Simulate known exception types
        class FakeInvalidURLError(Exception):
            pass

        class FakeRateLimitExceededException(Exception):
            pass

        # Note: We're testing the mapping by name, not actual exception types
        # because we don't want to import github exceptions
        assert (
            get_error_for_exception(ValueError("test")).code == E1001_INVALID_URL.code
        )
        assert (
            get_error_for_exception(TimeoutError("test")).code
            == E5004_TIMEOUT_ERROR.code
        )

    def test_get_error_for_exception_unknown_type(self):
        """Test mapping unknown exception types to internal error."""
        from ccpragents.domain.errors import (
            get_error_for_exception,
            E5001_INTERNAL_ERROR,
        )

        class CustomError(Exception):
            pass

        result = get_error_for_exception(CustomError("test"))
        assert result == E5001_INTERNAL_ERROR

    def test_create_error_response_basic(self):
        """Test creating basic error response."""
        from ccpragents.domain.errors import create_error_response, E1001_INVALID_URL

        response = create_error_response(E1001_INVALID_URL)

        assert response["success"] is False
        assert "error" in response
        assert response["error"]["error_code"] == "E1001_INVALID_URL"

    def test_create_error_response_with_detail(self):
        """Test creating error response with detail."""
        from ccpragents.domain.errors import create_error_response, E1001_INVALID_URL

        response = create_error_response(
            E1001_INVALID_URL, detail="Missing protocol in URL"
        )

        assert response["error"]["detail"] == "Missing protocol in URL"

    def test_create_error_response_with_context(self):
        """Test creating error response with context."""
        from ccpragents.domain.errors import create_error_response, E1001_INVALID_URL

        response = create_error_response(
            E1001_INVALID_URL, context={"provided_url": "invalid://url"}
        )

        assert "context" in response["error"]
        assert response["error"]["context"]["provided_url"] == "invalid://url"


# =============================================================================
# Integration Tests
# =============================================================================


class TestPhase3Integration:
    """Integration tests for Phase 3 improvements."""

    def test_file_patch_with_priority_and_smells(self):
        """Test FilePatchInfo with auto-detected priority and smells."""
        from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE

        # Create a security-related file with code smells
        patch = FilePatchInfo(
            filename="auth/token_handler.py",
            base_file="original code",
            head_file="new code",
            patch="+# TODO: add proper validation\n+password = 'hardcoded'\n+print('debug')",
            edit_type=EDIT_TYPE.MODIFIED,
            num_plus_lines=3,
            num_minus_lines=0,
        )

        # Calculate priority
        priority = patch.calculate_review_priority()
        assert priority == "high"  # Security file

        # Detect smells
        smells = patch.detect_code_smells()
        assert len(smells) > 0  # Should detect TODO and print

    def test_pr_diff_with_full_metadata(self):
        """Test PRDiff with complete metadata."""
        from ccpragents.domain.entities.pr_diff import PRDiff

        diff = PRDiff(
            diff_content="@@ -1,10 +1,15 @@\n-old\n+new",
            commit_messages="1. Add feature\n2. Fix bug",
            files_changed=5,
            total_additions=100,
            total_deletions=30,
            generation_metadata={
                "cache_hit": False,
                "generation_time_ms": 250,
                "parallel_processing": True,
            },
            file_summaries=[
                {"filename": "file1.py", "additions": 50, "deletions": 10},
                {"filename": "file2.py", "additions": 50, "deletions": 20},
            ],
        )

        # Get full response envelope
        envelope = diff.get_response_envelope()

        assert envelope["statistics"]["total_changes"] == 130
        assert envelope["metadata"]["cache_hit"] is False
        assert len(envelope["file_summaries"]) == 2

    def test_error_handling_flow(self):
        """Test complete error handling flow."""
        from ccpragents.domain.errors import (
            MCPError,
            E1001_INVALID_URL,
            create_error_response,
        )

        # Simulate error occurrence
        try:
            raise MCPError(E1001_INVALID_URL, detail="No PR number in URL")
        except MCPError as e:
            response = create_error_response(
                e.error_code, detail=e.detail, context=e.context
            )

        assert response["success"] is False
        assert response["error"]["detail"] == "No PR number in URL"
        assert "remediation" in response["error"]
