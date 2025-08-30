"""Diff utility for patch generation and manipulation."""
import difflib
import re
from typing import Union
from ccpragents.domain.services.diff import DiffServiceInterface
from ccpragents.infrastructure.logging.console_logger import get_logger


class DiffUtils(DiffServiceInterface):
    """Utility for diff generation, patch extension, and content decoding.

    This class provides functionality for creating unified diffs, extending
    patches with full context, and handling content encoding issues.
    """

    RE_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[ ]?(.*)")

    def __init__(self, logger=None):
        """Initialize the diff utility.

        Args:
            logger: Logger instance for logging operations
        """
        self._logger = logger or get_logger()

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
        header = f'@@ -{start1},{orig_count} +{start2},{new_count} @@'
        body_lines = []
        sm = difflib.SequenceMatcher(None, orig_lines, new_lines)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                for k in range(i1, i2):
                    body_lines.append(' ' + orig_lines[k])
            elif tag == 'delete':
                for k in range(i1, i2):
                    body_lines.append('-' + orig_lines[k])
            elif tag == 'insert':
                for k in range(j1, j2):
                    body_lines.append('+' + new_lines[k])
            elif tag == 'replace':
                for k in range(i1, i2):
                    body_lines.append('-' + orig_lines[k])
                for k in range(j1, j2):
                    body_lines.append('+' + new_lines[k])

        # keep a leading blank line to match previous formatting between hunks
        return '\n'.join(['', header] + body_lines)

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
                return content.decode('utf-8')
            except UnicodeDecodeError:
                encodings_to_try = ['iso-8859-1', 'latin-1', 'ascii', 'utf-16']
                for encoding in encodings_to_try:
                    try:
                        return content.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                return ""
        return content

    def extend_patch(self, original_file_str: str, patch_str: str, new_file_str: str = "") -> str:
        """Extend a patch to show full file context instead of just changed lines.

        Args:
            original_file_str: Original file content (before changes)
            patch_str: Original patch string (fallback if extension fails)
            new_file_str: New file content (after changes), defaults to empty string

        Returns:
            str: Extended patch with full file context, original patch on failure
        """
        original_file_str = self.decode_if_bytes(original_file_str)
        new_file_str = self.decode_if_bytes(new_file_str)

        # Allow full-file context even for new files (original can be empty)
        original_file_str = original_file_str or ""
        new_file_str = new_file_str or ""

        try:
            # Build a single full-file unified-diff hunk
            extended_patch_str = self.build_full_file_patch(original_file_str, new_file_str)
        except Exception as e:
            self._logger.warning(f"Failed to extend patch: {e}")
            return patch_str

        return extended_patch_str

    def extract_hunk_headers(self, match: re.Match) -> tuple:
        """Extract and parse hunk header information from regex match.

        Args:
            match: Regex match object from hunk header pattern

        Returns:
            tuple: (section_header, size1, size2, start1, start2) containing:
                - section_header: Additional header text after @@
                - size1: Number of lines in original file section
                - size2: Number of lines in new file section
                - start1: Starting line number in original file
                - start2: Starting line number in new file

        Note:
            Handles edge cases like '@@ -0,0 +1 @@' for new files
        """
        res = list(match.groups())
        for i in range(len(res)):
            if res[i] is None:
                res[i] = 0
        try:
            start1, size1, start2, size2 = map(int, res[:4])
        except (ValueError, IndexError):  # '@@ -0,0 +1 @@' case
            start1, size1, size2 = map(int, res[:3])
            start2 = 0
        section_header = res[4]
        return section_header, size1, size2, start1, start2


def get_diff_utils() -> DiffUtils:
    """Get a diff utils instance.

    Returns:
        DiffUtils: Diff utilities instance
    """
    return DiffUtils()
