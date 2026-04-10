"""Diff utility for patch generation and manipulation."""

import difflib
import re
import logging
from dataclasses import dataclass
from prdiffer.domain.services.diff import DiffServiceInterface
from prdiffer.infrastructure.utils.logger_factory import LazyLoggerMixin


DEFAULT_LARGE_FILE_THRESHOLD = 5000  # Lines
DEFAULT_DIFF_CHUNK_SIZE = 1000  # Lines per chunk
DEFAULT_MAX_DIFF_SIZE = 100000  # Maximum diff size (100K lines)


@dataclass(frozen=True)
class DiffProcessingConfig:
    """Configuration for diff processing of large files."""

    large_file_threshold: int = DEFAULT_LARGE_FILE_THRESHOLD
    chunk_size: int = DEFAULT_DIFF_CHUNK_SIZE
    max_diff_size: int = DEFAULT_MAX_DIFF_SIZE

    def validate(self) -> "DiffProcessingConfig":
        """Validate configuration and return a corrected version if needed."""
        return DiffProcessingConfig(
            large_file_threshold=max(100, min(50000, self.large_file_threshold)),
            chunk_size=max(100, min(10000, self.chunk_size)),
            max_diff_size=max(1000, min(1000000, self.max_diff_size)),
        )


class DiffUtils(LazyLoggerMixin, DiffServiceInterface):
    """Utility for diff generation, patch extension, and content decoding.

    This class provides functionality for creating unified diffs, extending
    patches with full context, and handling content encoding issues.
    """

    RE_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[ ]?(.*)")

    def __init__(self, logger: logging.Logger | None = None, config: DiffProcessingConfig | None = None) -> None:
        self._init_lazy_logger(logger, __name__)
        self._config = (config or DiffProcessingConfig()).validate()

    def build_full_file_patch(self, original_file_str: str, new_file_str: str) -> str:
        """Build a single unified-diff hunk that covers the entire file."""
        orig_lines = original_file_str.splitlines()
        new_lines = new_file_str.splitlines()

        orig_count = len(orig_lines)
        new_count = len(new_lines)
        start1 = 0 if orig_count == 0 else 1
        start2 = 0 if new_count == 0 else 1
        header = f"@@ -{start1},{orig_count} +{start2},{new_count} @@"
        body_lines: list[str] = []
        sm = difflib.SequenceMatcher(None, orig_lines, new_lines)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i1, i2):
                    body_lines.append(" " + orig_lines[k])
            elif tag == "delete":
                for k in range(i1, i2):
                    body_lines.append("-" + orig_lines[k])
            elif tag == "insert":
                for k in range(j1, j2):
                    body_lines.append("+" + new_lines[k])
            elif tag == "replace":
                for k in range(i1, i2):
                    body_lines.append("-" + orig_lines[k])
                for k in range(j1, j2):
                    body_lines.append("+" + new_lines[k])

        return "\n".join(["", header] + body_lines)

    def build_full_file_patch_chunked(
        self,
        original_file_str: str,
        new_file_str: str,
        chunk_size: int | None = None,
        large_file_threshold: int | None = None,
    ) -> str:
        """Build a unified diff with chunked processing for large files.

        For files larger than large_file_threshold, splits processing into
        chunks to avoid O(N²) complexity issues with difflib.SequenceMatcher.
        """
        chunk_size = chunk_size if chunk_size is not None else self._config.chunk_size
        large_file_threshold = large_file_threshold if large_file_threshold is not None else self._config.large_file_threshold
        max_diff_size = self._config.max_diff_size

        orig_lines = original_file_str.splitlines()
        new_lines = new_file_str.splitlines()

        max_lines = max(len(orig_lines), len(new_lines))
        if max_lines > max_diff_size:
            return "[LARGE FILE - DIFF TRUNCATED: File exceeds maximum diff size]"

        if max_lines <= large_file_threshold:
            return self.build_full_file_patch(original_file_str, new_file_str)

        self._get_logger().info(f"Using chunked diff processing for large file ({max_lines} lines)")

        hunks: list[str] = []
        chunk_index = 0

        while chunk_index * chunk_size < max_lines:
            start_line = chunk_index * chunk_size
            end_line = min((chunk_index + 1) * chunk_size, max_lines)

            orig_chunk = orig_lines[start_line:end_line]
            new_chunk = new_lines[start_line:end_line]

            hunk = self._build_chunk_hunk(orig_chunk, new_chunk, start_line + 1, start_line + 1)
            if hunk:
                hunks.append(hunk)

            chunk_index += 1

        return "\n".join(hunks) if hunks else ""

    def _build_chunk_hunk(
        self,
        orig_lines: list[str],
        new_lines: list[str],
        orig_start: int,
        new_start: int,
    ) -> str:
        """Build a diff hunk for a chunk of lines."""
        if not orig_lines and not new_lines:
            return ""

        orig_count = len(orig_lines)
        new_count = len(new_lines)

        header = f"@@ -{orig_start},{orig_count} +{new_start},{new_count} @@"
        body_lines: list[str] = []

        sm = difflib.SequenceMatcher(None, orig_lines, new_lines)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i1, i2):
                    body_lines.append(" " + orig_lines[k])
            elif tag == "delete":
                for k in range(i1, i2):
                    body_lines.append("-" + orig_lines[k])
            elif tag == "insert":
                for k in range(j1, j2):
                    body_lines.append("+" + new_lines[k])
            elif tag == "replace":
                for k in range(i1, i2):
                    body_lines.append("-" + orig_lines[k])
                for k in range(j1, j2):
                    body_lines.append("+" + new_lines[k])

        if any(line.startswith("+") or line.startswith("-") for line in body_lines):
            return "\n".join(["", header] + body_lines)
        return ""

    def decode_if_bytes(self, content: str | bytes | bytearray) -> str:
        """Decode bytes content to string with fallback encoding support.

        Tries UTF-8 first, then falls back to iso-8859-1, latin-1, ascii, utf-16.
        Returns empty string if all decodings fail.
        """
        if isinstance(content, (bytes, bytearray)):
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                encodings_to_try = ["iso-8859-1", "latin-1", "ascii", "utf-16"]
                for encoding in encodings_to_try:
                    try:
                        return content.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                return ""
        return content

    def extend_patch(self, original_file_str: str, patch_str: str, new_file_str: str = "") -> str:
        """Extend a patch to show full file context instead of just changed lines."""
        original_file_str = self.decode_if_bytes(original_file_str)
        new_file_str = self.decode_if_bytes(new_file_str)

        original_file_str = original_file_str or ""
        new_file_str = new_file_str or ""

        if self._is_binary_content(original_file_str) or self._is_binary_content(new_file_str):
            self._get_logger().debug("Skipping diff for binary file content")
            return "[BINARY FILE - DIFF NOT AVAILABLE]"

        try:
            max_lines = max(len(original_file_str.splitlines()), len(new_file_str.splitlines()))
            if max_lines > self._config.large_file_threshold:
                extended_patch_str = self.build_full_file_patch_chunked(original_file_str, new_file_str)
            else:
                extended_patch_str = self.build_full_file_patch(original_file_str, new_file_str)
        except Exception as e:
            self._get_logger().warning(f"Failed to extend patch: {e}")
            return patch_str

        return extended_patch_str

    def _is_binary_content(self, content: str) -> bool:
        """Check if string content appears to be binary."""
        if not content:
            return False

        if "\x00" in content:
            return True

        # Sample first 8KB for efficiency
        sample = content[:8192]
        non_printable = sum(1 for c in sample if ord(c) < 32 and c not in "\n\r\t")

        if len(sample) > 0 and non_printable / len(sample) > 0.3:
            return True

        return False


def get_diff_utils(logger: logging.Logger | None = None, config: DiffProcessingConfig | None = None) -> DiffUtils:
    """Get a diff utils instance."""
    return DiffUtils(logger=logger, config=config)
