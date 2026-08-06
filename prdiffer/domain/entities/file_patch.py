from dataclasses import dataclass, field
from enum import StrEnum
import re
from typing import Any

# Git-style six-digit octal mode (e.g. 100644, 100755, 120000).
_GIT_MODE_RE = re.compile(r"^[0-7]{6}$")


class EDIT_TYPE(StrEnum):
    """File edit type enumeration."""

    ADDED = "added"
    DELETED = "deleted"
    MODIFIED = "modified"
    RENAMED = "renamed"
    UNKNOWN = "unknown"


def _validate_optional_git_mode(name: str, value: object) -> None:
    """Reject present-but-malformed Git mode strings; None is allowed."""
    if value is None:
        return
    if not isinstance(value, str) or not _GIT_MODE_RE.fullmatch(value):
        raise ValueError(f"{name} must be a six-digit octal Git mode string (got {value!r})")


@dataclass(frozen=True)
class FilePatchInfo:
    """Domain entity representing a file change in a pull request.

    This entity contains comprehensive information about a single file change,
    including content, metadata, and analysis results. It represents the
    complete context of how a file has changed in a PR.
    """

    filename: str
    base_file: str = ""
    head_file: str = ""
    patch: str = ""

    edit_type: EDIT_TYPE = EDIT_TYPE.UNKNOWN
    old_filename: str | None = None
    language: str | None = None

    num_plus_lines: int = 0
    num_minus_lines: int = 0

    ai_file_summary: str | None = None
    tokens: int = -1

    # Optional Git file modes (six-digit octal). Absent modes leave generation unchanged.
    old_mode: str | None = None
    new_mode: str | None = None

    # Phase 3: Extended metadata for API enhancement
    diff_metadata: dict[str, Any] | None = None
    code_smell_indicators: tuple[str, ...] | None = None
    suggested_review_priority: str = "normal"  # "high", "normal", "low"

    _file_extension: str | None = field(init=False, default=None, compare=False)
    _is_binary: bool = field(init=False, default=False, compare=False)
    _change_percentage: float = field(init=False, default=0.0, compare=False)

    def __post_init__(self):
        _validate_optional_git_mode("old_mode", self.old_mode)
        _validate_optional_git_mode("new_mode", self.new_mode)
        object.__setattr__(self, "_file_extension", self._extract_file_extension())
        object.__setattr__(self, "_is_binary", self._detect_binary_file())
        object.__setattr__(self, "_change_percentage", self._calculate_change_percentage())

    def _extract_file_extension(self) -> str | None:
        """Extract file extension from filename."""
        if "." in self.filename:
            return "." + self.filename.split(".")[-1].lower()
        return None

    def _detect_binary_file(self) -> bool:
        """Detect if file is binary based on content and extension."""
        binary_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".ico",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".zip",
            ".tar",
            ".gz",
            ".7z",
            ".rar",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
        }

        if self._file_extension in binary_extensions:
            return True

        if self.head_file:
            try:
                self.head_file.encode("utf-8").decode("utf-8")
                return False
            except UnicodeDecodeError:
                return True

        return False

    def _calculate_change_percentage(self) -> float:
        """Calculate percentage of lines changed (0.0 to 100.0)."""
        total_lines = self.num_plus_lines + self.num_minus_lines
        if total_lines == 0:
            return 0.0

        original_lines = len(self.base_file.splitlines()) if self.base_file else 1
        if original_lines == 0:
            return 0.0

        return min((total_lines / original_lines) * 100, 100.0)

    @property
    def file_extension(self) -> str | None:
        return self._file_extension

    @property
    def is_binary(self) -> bool:
        return self._is_binary

    @property
    def change_percentage(self) -> float:
        return self._change_percentage

    @property
    def total_changes(self) -> int:
        return self.num_plus_lines + self.num_minus_lines

    @property
    def is_significant_change(self) -> bool:
        """Check if this represents a significant file change.

        A change is considered significant if:
        - It has more than 50 total changes, OR
        - It's a file addition or deletion, OR
        - It's a renamed file

        Returns:
            bool: True if change is significant
        """
        return self.total_changes > 50 or self.edit_type in (
            EDIT_TYPE.ADDED,
            EDIT_TYPE.DELETED,
            EDIT_TYPE.RENAMED,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the file change."""
        return {
            "filename": self.filename,
            "edit_type": self.edit_type,
            "total_changes": self.total_changes,
            "additions": self.num_plus_lines,
            "deletions": self.num_minus_lines,
            "change_percentage": round(self.change_percentage, 2),
            "language": self.language,
            "is_binary": self.is_binary,
            "is_significant": self.is_significant_change,
            "file_extension": self.file_extension,
            "review_priority": self.suggested_review_priority,
            "code_smell_indicators": self.code_smell_indicators,
        }

    def calculate_review_priority(self) -> str:
        """Calculate suggested review priority based on file characteristics."""
        high_priority_patterns = [
            "security",
            "auth",
            "password",
            "token",
            "secret",
            "config",
            ".env",
            "credential",
        ]

        low_priority_patterns = [
            "test",
            ".md",
            "readme",
            "doc",
            "changelog",
            ".txt",
            "license",
        ]

        filename_lower = self.filename.lower()

        for pattern in high_priority_patterns:
            if pattern in filename_lower:
                return "high"

        if self.total_changes > 100 or self.change_percentage > 50:
            return "high"

        for pattern in low_priority_patterns:
            if pattern in filename_lower:
                return "low"

        return "normal"

    def detect_code_smells(self) -> list[str]:
        """Detect potential code smell indicators in the diff."""
        indicators: list[str] = []

        if not self.patch:
            return indicators

        patch_lower = self.patch.lower()

        code_smell_patterns = {
            "TODO": "Contains TODO comments",
            "FIXME": "Contains FIXME comments",
            "HACK": "Contains HACK comments",
            "XXX": "Contains XXX markers",
            "console.log": "Contains debug console.log",
            "print(": "Contains debug print statements",
            "debugger": "Contains debugger statements",
            "sleep(": "Contains sleep/delay calls",
            "password": "Contains potential hardcoded password",
            "api_key": "Contains potential hardcoded API key",
        }

        for pattern, indicator in code_smell_patterns.items():
            if pattern.lower() in patch_lower:
                indicators.append(indicator)

        if self.total_changes > 500:
            indicators.append("Very large change set - consider splitting")

        if self.edit_type == EDIT_TYPE.DELETED:
            indicators.append("File deleted - verify intended")

        return indicators

    def validate(self) -> list[str]:
        """Validate the file patch information."""
        errors: list[str] = []

        if not self.filename or not self.filename.strip():
            errors.append("Filename cannot be empty")

        if self.num_plus_lines < 0:
            errors.append("Number of plus lines cannot be negative")

        if self.num_minus_lines < 0:
            errors.append("Number of minus lines cannot be negative")

        if self.edit_type == EDIT_TYPE.RENAMED and not self.old_filename:
            errors.append("Old filename is required for renamed files")

        if self.edit_type not in EDIT_TYPE:
            errors.append(f"Invalid edit type: {self.edit_type}")

        return errors

    def is_ignored_file(self, ignore_patterns: list[str] | None = None) -> bool:
        """Check if file should be ignored based on patterns.

        Args:
            ignore_patterns: List of patterns to ignore (optional)

        Returns:
            bool: True if file matches ignore patterns
        """
        if not ignore_patterns:
            return False

        filename = self.filename.lower()
        for pattern in ignore_patterns:
            if pattern.lower() in filename:
                return True

        return False

    def get_diff_statistics(self) -> dict[str, Any]:
        """Get detailed diff statistics."""
        if not self.patch:
            return {
                "hunks": 0,
                "context_lines": 0,
                "addition_lines": 0,
                "deletion_lines": 0,
                "diff_lines": [],
            }

        hunks = 0
        context_lines = 0
        addition_lines = 0
        deletion_lines = 0
        diff_lines: list[str] = []

        for line in self.patch.splitlines():
            diff_lines.append(line)
            if line.startswith("@@"):
                hunks += 1
            elif line.startswith(" "):
                context_lines += 1
            elif line.startswith("+") and not line.startswith("+++"):
                addition_lines += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletion_lines += 1

        return {
            "hunks": hunks,
            "context_lines": context_lines,
            "addition_lines": addition_lines,
            "deletion_lines": deletion_lines,
            "diff_lines": diff_lines,
            "total_diff_lines": len(diff_lines),
        }

    def format_for_display(self, max_context_lines: int = 10) -> str:
        """Format the diff for human display with limited context."""
        if not self.patch:
            return f"Empty diff for {self.filename}"

        lines = self.patch.splitlines()
        if len(lines) <= max_context_lines:
            return self.patch

        header_lines = min(max_context_lines // 2, len(lines))
        footer_lines = max_context_lines - header_lines

        displayed_lines = lines[:header_lines] + ["..."] + lines[-footer_lines:]
        return "\n".join(displayed_lines)
