"""Diff utility for patch generation and manipulation."""

import difflib
import re
import threading
from dataclasses import dataclass
from typing import Union, Optional, List
from prdiffer.domain.services import DiffServiceInterface


# Default configuration for large file processing
DEFAULT_LARGE_FILE_THRESHOLD = 5000  # Lines
DEFAULT_DIFF_CHUNK_SIZE = 1000  # Lines per chunk
DEFAULT_MAX_DIFF_SIZE = 100000  # Maximum diff size (100K lines)


@dataclass(frozen=True)
class DiffProcessingConfig:
    """Configuration for diff processing of large files.

    Attributes:
        large_file_threshold: Line count threshold for enabling chunked processing
        chunk_size: Number of lines to process per chunk for large files
        max_diff_size: Maximum file size in lines for diff generation
    """

    large_file_threshold: int = DEFAULT_LARGE_FILE_THRESHOLD
    chunk_size: int = DEFAULT_DIFF_CHUNK_SIZE
    max_diff_size: int = DEFAULT_MAX_DIFF_SIZE

    def validate(self) -> "DiffProcessingConfig":
        """Validate configuration and return a corrected version if needed.

        Returns:
            DiffProcessingConfig: Validated configuration with applied constraints
        """
        return DiffProcessingConfig(
            large_file_threshold=max(100, min(50000, self.large_file_threshold)),
            chunk_size=max(100, min(10000, self.chunk_size)),
            max_diff_size=max(1000, min(1000000, self.max_diff_size)),
        )


class DiffUtils(DiffServiceInterface):
    """Utility for diff generation, patch extension, and content decoding.

    This class provides functionality for creating unified diffs, extending
    patches with full context, and handling content encoding issues.
    """

    RE_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[ ]?(.*)")

    def __init__(self, logger=None, config: Optional[DiffProcessingConfig] = None):
        """Initialize the diff utility.

        Args:
            logger: Logger instance for logging operations
            config: Optional diff processing configuration (uses defaults if not provided)
        """
        self._logger = logger
        self._logger_fetched = logger is not None
        self._logger_lock = threading.Lock()
        self._config = (config or DiffProcessingConfig()).validate()

    def _get_logger(self):
        """Get logger instance, lazily loading if needed to avoid circular imports.

        Uses double-checked locking pattern for thread safety.
        """
        if not self._logger_fetched:
            with self._logger_lock:
                # Double-check pattern to avoid race conditions
                if not self._logger_fetched:
                    from prdiffer.infrastructure.logging.console_logger import (
                        get_logger,
                    )

                    self._logger = get_logger()
                    self._logger_fetched = True
        return self._logger

    def build_full_file_patch(self, original_file_str: str, new_file_str: str) -> str:
        """Build a single unified-diff hunk that covers the entire file.

        Args:
            original_file_str: Original file content
            new_file_str: New file content

        Returns:
            str: Unified diff patch marking unchanged lines with ' ',
                 additions with '+', and deletions with '-'
        """
        orig_lines = original_file_str.splitlines()
        new_lines = new_file_str.splitlines()

        orig_count = len(orig_lines)
        new_count = len(new_lines)
        start1 = 0 if orig_count == 0 else 1
        start2 = 0 if new_count == 0 else 1
        header = f"@@ -{start1},{orig_count} +{start2},{new_count} @@"
        body_lines = []
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

        # keep a leading blank line to match previous formatting between hunks
        return "\n".join(["", header] + body_lines)

    def build_full_file_patch_chunked(
        self,
        original_file_str: str,
        new_file_str: str,
        chunk_size: Optional[int] = None,
        large_file_threshold: Optional[int] = None,
    ) -> str:
        """Build a unified diff with chunked processing for large files.

        For files larger than large_file_threshold, splits processing into
        chunks to avoid O(N²) complexity issues with difflib.SequenceMatcher.

        Args:
            original_file_str: Original file content
            new_file_str: New file content
            chunk_size: Number of lines per chunk (uses config default if not specified)
            large_file_threshold: Threshold for chunked processing (uses config default if not specified)

        Returns:
            str: Unified diff patch, or "[LARGE FILE - DIFF TRUNCATED]" if too large
        """
        # Use config values if not specified
        chunk_size = chunk_size if chunk_size is not None else self._config.chunk_size
        large_file_threshold = (
            large_file_threshold
            if large_file_threshold is not None
            else self._config.large_file_threshold
        )
        max_diff_size = self._config.max_diff_size

        orig_lines = original_file_str.splitlines()
        new_lines = new_file_str.splitlines()

        # Check if file is too large
        max_lines = max(len(orig_lines), len(new_lines))
        if max_lines > max_diff_size:
            return "[LARGE FILE - DIFF TRUNCATED: File exceeds maximum diff size]"

        # Use standard processing for small files
        if max_lines <= large_file_threshold:
            return self.build_full_file_patch(original_file_str, new_file_str)

        # Chunked processing for large files
        self._get_logger().info(
            f"Using chunked diff processing for large file ({max_lines} lines)"
        )

        hunks = []
        chunk_index = 0

        while chunk_index * chunk_size < max_lines:
            start_line = chunk_index * chunk_size
            end_line = min((chunk_index + 1) * chunk_size, max_lines)

            # Get chunks from both files
            orig_chunk = orig_lines[start_line:end_line]
            new_chunk = new_lines[start_line:end_line]

            # Generate hunk for this chunk
            hunk = self._build_chunk_hunk(
                orig_chunk, new_chunk, start_line + 1, start_line + 1
            )
            if hunk:
                hunks.append(hunk)

            chunk_index += 1

        return "\n".join(hunks) if hunks else ""

    def _build_chunk_hunk(
        self,
        orig_lines: List[str],
        new_lines: List[str],
        orig_start: int,
        new_start: int,
    ) -> str:
        """Build a diff hunk for a chunk of lines.

        Args:
            orig_lines: Original lines in this chunk
            new_lines: New lines in this chunk
            orig_start: Starting line number in original file
            new_start: Starting line number in new file

        Returns:
            str: Unified diff hunk for this chunk
        """
        if not orig_lines and not new_lines:
            return ""

        orig_count = len(orig_lines)
        new_count = len(new_lines)

        header = f"@@ -{orig_start},{orig_count} +{new_start},{new_count} @@"
        body_lines = []

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

        # Only return hunk if there are actual changes
        if any(line.startswith("+") or line.startswith("-") for line in body_lines):
            return "\n".join(["", header] + body_lines)
        return ""

    def decode_if_bytes(self, content: Union[str, bytes, bytearray]) -> str:
        """Decode bytes content to string with fallback encoding support.

        Args:
            content: Content that may be bytes, bytearray, or string

        Returns:
            str: Decoded string content, empty string if all decodings fail

        Note:
            Tries UTF-8 first, then falls back to iso-8859-1, latin-1, ascii, utf-16
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

    def extend_patch(
        self, original_file_str: str, patch_str: str, new_file_str: str = ""
    ) -> str:
        """Extend a patch to show full file context instead of just changed lines.

        Args:
            original_file_str: Original file content (before changes)
            patch_str: Original patch string (fallback if extension fails)
            new_file_str: New file content (after changes), defaults to empty string

        Returns:
            str: Extended patch with full file context, original patch on failure,
                 or "[BINARY FILE]" marker if binary content detected
        """
        original_file_str = self.decode_if_bytes(original_file_str)
        new_file_str = self.decode_if_bytes(new_file_str)

        # Allow full-file context even for new files (original can be empty)
        original_file_str = original_file_str or ""
        new_file_str = new_file_str or ""

        # Pre-check for binary content before attempting diff generation
        if self._is_binary_content(original_file_str) or self._is_binary_content(
            new_file_str
        ):
            self._get_logger().debug("Skipping diff for binary file content")
            return "[BINARY FILE - DIFF NOT AVAILABLE]"

        try:
            # Use chunked processing for large files to avoid O(N²) complexity
            max_lines = max(
                len(original_file_str.splitlines()), len(new_file_str.splitlines())
            )
            if max_lines > self._config.large_file_threshold:
                extended_patch_str = self.build_full_file_patch_chunked(
                    original_file_str, new_file_str
                )
            else:
                # Build a single full-file unified-diff hunk
                extended_patch_str = self.build_full_file_patch(
                    original_file_str, new_file_str
                )
        except Exception as e:
            self._get_logger().warning(f"Failed to extend patch: {e}")
            return patch_str

        return extended_patch_str

    def _is_binary_content(self, content: str) -> bool:
        """Check if string content appears to be binary.

        Args:
            content: String content to check

        Returns:
            bool: True if content appears to be binary
        """
        if not content:
            return False

        # Check for null bytes (common in binary files)
        if "\x00" in content:
            return True

        # Check for high ratio of non-printable characters
        # Sample first 8KB for efficiency
        sample = content[:8192]
        non_printable = sum(1 for c in sample if ord(c) < 32 and c not in "\n\r\t")

        # If more than 30% non-printable, likely binary
        if len(sample) > 0 and non_printable / len(sample) > 0.3:
            return True

        return False


def get_diff_utils(
    logger=None, config: Optional[DiffProcessingConfig] = None
) -> DiffUtils:
    """Get a diff utils instance.

    Args:
        logger: Optional logger instance
        config: Optional diff processing configuration

    Returns:
        DiffUtils: Diff utilities instance
    """
    return DiffUtils(logger=logger, config=config)
