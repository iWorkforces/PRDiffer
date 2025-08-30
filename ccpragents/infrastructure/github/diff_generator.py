"""Diff generation and patch processing service."""
import re
from typing import List
from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE
from ccpragents.domain.services.diff import DiffServiceInterface
from ccpragents.infrastructure.logging.console_logger import get_logger


class DiffGenerator:
    """Service for generating extended diffs and processing patches.

    This class handles the creation of extended diff output with full file context,
    hunk processing, and formatting for pull request diff analysis.
    """

    RE_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[ ]?(.*)")

    def __init__(self, diff_utils: DiffServiceInterface, logger=None):
        """Initialize the diff generator.

        Args:
            diff_utils: Service for diff utilities
            logger: Logger instance for logging operations
        """
        self._diff_utils = diff_utils
        self._logger = logger or get_logger()

    def generate_extended_diff(self,
                              diff_files: List[FilePatchInfo],
                              add_line_numbers_to_hunks: bool = False) -> List[str]:
        """Generate an extended diff for a pull request.

        Args:
            diff_files: List of FilePatchInfo objects to process
            add_line_numbers_to_hunks: Whether to add line numbers to hunks

        Returns:
            List of extended diff strings, one per file
        """
        extended_diffs = []
        for file in diff_files:
            original_file_content_str = file.base_file
            new_file_content_str = file.head_file
            patch = file.patch
            if not patch:
                continue

            # extend each patch with extra lines of context
            extended_patch = self._diff_utils.extend_patch(
                original_file_content_str, patch, new_file_str=new_file_content_str
            )
            if not extended_patch:
                self._logger.warning(f"Failed to extend patch for file: {file.filename}")
                continue

            if add_line_numbers_to_hunks:
                full_extended_patch = self._decouple_and_convert_to_hunks_with_lines_numbers(
                    extended_patch, file
                )
            else:
                full_extended_patch = f"\n\n## File: '{file.filename.strip()}'\n\n{extended_patch.rstrip()}\n"
            extended_diffs.append(full_extended_patch)
        return extended_diffs

    def _decouple_and_convert_to_hunks_with_lines_numbers(self, patch: str, file: FilePatchInfo) -> str:
        """Convert a given patch string into a string with line numbers for each hunk.

        This method processes patch hunks to display new and old content sections
        with line numbers, making it easier to understand the changes.

        Args:
            patch: The patch string to be converted
            file: FilePatchInfo object containing the filename and metadata

        Returns:
            str: A string with line numbers for each hunk, indicating the new and old content

        Example output:
            ## src/file.ts
            __new hunk__
            881        line1
            882        line2
            883        line3
            887 +      line4
            888 +      line5
            889        line6
            890        line7
            ...
            __old hunk__
                    line1
                    line2
            -       line3
            -       line4
                    line5
                    line6
                    ...
        """

        # Add a header for the file
        if file:
            # if the file was deleted, return a message indicating that the file was deleted
            if hasattr(file, 'edit_type') and file.edit_type == EDIT_TYPE.DELETED:
                return f"\n\n## File '{file.filename.strip()}' was deleted\n"

            patch_with_lines_str = f"\n\n## File: '{file.filename.strip()}'\n"
        else:
            patch_with_lines_str = ""

        patch_lines = patch.splitlines()
        RE_HUNK_HEADER = self.RE_HUNK_HEADER
        new_content_lines = []
        old_content_lines = []
        match = None
        start1, size1, start2, size2 = -1, -1, -1, -1
        prev_header_line = []
        header_line = []

        for line_i, line in enumerate(patch_lines):
            if 'no newline at end of file' in line.lower():
                continue

            if line.startswith('@@'):
                header_line = line
                match = RE_HUNK_HEADER.match(line)
                if match and (new_content_lines or old_content_lines):  # found a new hunk, split the previous lines
                    if prev_header_line:
                        patch_with_lines_str += f'\n{prev_header_line}\n'
                    is_plus_lines = is_minus_lines = False
                    if new_content_lines:
                        is_plus_lines = any([line.startswith('+') for line in new_content_lines])
                    if old_content_lines:
                        is_minus_lines = any([line.startswith('-') for line in old_content_lines])
                    if is_plus_lines or is_minus_lines:  # notice 'True' here - we always present __new hunk__ for section, otherwise LLM gets confused
                        patch_with_lines_str = patch_with_lines_str.rstrip() + '\n__new hunk__\n'
                        for i, line_new in enumerate(new_content_lines):
                            patch_with_lines_str += f"{start2 + i} {line_new}\n"
                    if is_minus_lines:
                        patch_with_lines_str = patch_with_lines_str.rstrip() + '\n__old hunk__\n'
                        for line_old in old_content_lines:
                            patch_with_lines_str += f"{line_old}\n"
                    new_content_lines = []
                    old_content_lines = []
                if match:
                    prev_header_line = header_line
                    section_header, size1, size2, start1, start2 = self._extract_hunk_headers(match)

            elif line.startswith('+'):
                new_content_lines.append(line)
            elif line.startswith('-'):
                old_content_lines.append(line)
            else:
                if not line and line_i:  # if this line is empty and the next line is a hunk header, skip it
                    if line_i + 1 < len(patch_lines) and patch_lines[line_i + 1].startswith('@@'):
                        continue
                    elif line_i + 1 == len(patch_lines):
                        continue
                new_content_lines.append(line)
                old_content_lines.append(line)

        # finishing last hunk
        if match and new_content_lines:
            patch_with_lines_str += f'\n{header_line}\n'
            is_plus_lines = is_minus_lines = False
            if new_content_lines:
                is_plus_lines = any([line.startswith('+') for line in new_content_lines])
            if old_content_lines:
                is_minus_lines = any([line.startswith('-') for line in old_content_lines])
            if is_plus_lines or is_minus_lines:  # notice 'True' here - we always present __new hunk__ for section, otherwise LLM gets confused
                patch_with_lines_str = patch_with_lines_str.rstrip() + '\n__new hunk__\n'
                for i, line_new in enumerate(new_content_lines):
                    patch_with_lines_str += f"{start2 + i} {line_new}\n"
            if is_minus_lines:
                patch_with_lines_str = patch_with_lines_str.rstrip() + '\n__old hunk__\n'
                for line_old in old_content_lines:
                    patch_with_lines_str += f"{line_old}\n"

        return patch_with_lines_str.rstrip()

    def _extract_hunk_headers(self, match: re.Match) -> tuple:
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

    def get_commit_messages(self, pull_request) -> str:
        """Retrieve and format all commit messages from the pull request.

        Args:
            pull_request: GitHub pull request object

        Returns:
            str: Formatted string with numbered commit messages, empty string on error

        Note:
            Each commit message is prefixed with its sequence number (1-based)
        """
        try:
            commit_list = pull_request.get_commits()
            commit_messages = [commit.commit.message for commit in commit_list]
            commit_messages_str = "\n".join([f"{i + 1}. {message}" for i, message in enumerate(commit_messages)])
        except Exception:
            commit_messages_str = ""
        return commit_messages_str


def get_diff_generator(diff_utils: DiffServiceInterface) -> DiffGenerator:
    """Get a configured diff generator instance.

    Args:
        diff_utils: Service for diff utilities

    Returns:
        DiffGenerator: Configured diff generator instance
    """
    return DiffGenerator(diff_utils=diff_utils)
