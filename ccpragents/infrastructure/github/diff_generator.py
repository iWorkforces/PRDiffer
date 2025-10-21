"""Diff generation and patch processing service."""

import re
import time
from typing import List, Dict, Optional, Tuple
from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE
from ccpragents.domain.services import DiffServiceInterface
from ccpragents.infrastructure.logging.console_logger import get_logger


class DiffGenerator:
    """Service for generating extended diffs and processing patches.

    This class handles the creation of extended diff output with full file context,
    hunk processing, and formatting for pull request diff analysis.
    """

    RE_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[ ]?(.*)")

    def __init__(
        self,
        diff_utils: DiffServiceInterface,
        parallel_executor=None,
        parallel_enabled: bool = True,
        parallel_threshold: int = 3,
        logger=None,
    ):
        """Initialize the diff generator.

        Args:
            diff_utils: Service for diff utilities
            parallel_executor: Optional parallel executor for concurrent processing
            parallel_enabled: Whether to use parallel processing (default: True)
            parallel_threshold: Minimum number of files to trigger parallel processing (default: 3)
            logger: Logger instance for logging operations
        """
        self._diff_utils = diff_utils
        self._parallel_executor = parallel_executor
        self._parallel_enabled = parallel_enabled and parallel_executor is not None
        self._parallel_threshold = parallel_threshold
        self._logger = logger or get_logger()

    def generate_extended_diff(
        self, diff_files: List[FilePatchInfo], add_line_numbers_to_hunks: bool = False
    ) -> List[str]:
        """Generate an extended diff for a pull request.

        Uses adaptive strategy: parallel processing for multiple files (>= threshold),
        sequential processing for small sets of files.

        Args:
            diff_files: List of FilePatchInfo objects to process
            add_line_numbers_to_hunks: Whether to add line numbers to hunks

        Returns:
            List of extended diff strings, one per file
        """
        num_files = len(diff_files)

        # Adaptive strategy: use parallel processing if:
        # 1. Parallel processing is enabled
        # 2. Number of files meets or exceeds threshold
        # 3. Parallel executor is available
        use_parallel = (
            self._parallel_enabled
            and num_files >= self._parallel_threshold
            and self._parallel_executor is not None
        )

        if use_parallel:
            self._logger.debug(
                f"Using parallel processing for {num_files} files "
                f"(threshold: {self._parallel_threshold})"
            )
            return self._generate_extended_diff_parallel(
                diff_files, add_line_numbers_to_hunks
            )
        else:
            reason = "disabled" if not self._parallel_enabled else f"below threshold ({num_files} < {self._parallel_threshold})"
            self._logger.debug(
                f"Using sequential processing for {num_files} files (parallel {reason})"
            )
            return self._generate_extended_diff_sequential(
                diff_files, add_line_numbers_to_hunks
            )

    def _decouple_and_convert_to_hunks_with_lines_numbers(
        self, patch: str, file: FilePatchInfo, is_first_file: bool = False
    ) -> str:
        """Convert a given patch string into a string with line numbers for each hunk.

        This method processes patch hunks to display new and old content sections
        with line numbers, making it easier to understand the changes.

        Args:
            patch: The patch string to be converted
            file: FilePatchInfo object containing the filename and metadata
            is_first_file: Whether this is the first file in the diff

        Returns:
            str: A string with line numbers for each hunk, indicating the new and old content
        """
        # Generate file header
        patch_with_lines_str = self._generate_file_header(file, is_first_file)
        if file and hasattr(file, "edit_type") and file.edit_type == EDIT_TYPE.DELETED:
            return patch_with_lines_str

        # Process all hunks in the patch
        patch_lines = patch.splitlines()
        hunks = self._parse_hunks_from_patch(patch_lines)

        # Format each hunk with line numbers
        for hunk in hunks:
            patch_with_lines_str += self._format_hunk_with_line_numbers(hunk)

        return patch_with_lines_str.rstrip()

    def _generate_file_header(
        self, file: Optional[FilePatchInfo], is_first_file: bool
    ) -> str:
        """Generate the file header for the patch output.

        Args:
            file: FilePatchInfo object or None
            is_first_file: Whether this is the first file in the diff

        Returns:
            str: Formatted file header
        """
        if not file:
            return ""

        separator = "" if is_first_file else "\n\n---"

        # Handle deleted files
        if hasattr(file, "edit_type") and file.edit_type == EDIT_TYPE.DELETED:
            return f"{separator}\n## File '{file.filename.strip()}' was deleted\n"

        return f"{separator}\n## File: '{file.filename.strip()}'\n"

    def _parse_hunks_from_patch(self, patch_lines: List[str]) -> List[Dict]:
        """Parse hunks from patch lines.

        Args:
            patch_lines: List of patch lines

        Returns:
            List of hunk dictionaries containing header, new_lines, old_lines, start positions
        """
        hunks = []
        current_hunk = None
        RE_HUNK_HEADER = self.RE_HUNK_HEADER

        for line_i, line in enumerate(patch_lines):
            if "no newline at end of file" in line.lower():
                continue

            if line.startswith("@@"):
                # Save previous hunk if exists
                if current_hunk is not None:
                    hunks.append(current_hunk)

                # Start new hunk
                match = RE_HUNK_HEADER.match(line)
                if match:
                    section_header, size1, size2, start1, start2 = (
                        self._extract_hunk_headers(match)
                    )
                    current_hunk = {
                        "header": line,
                        "new_lines": [],
                        "old_lines": [],
                        "start1": start1,
                        "start2": start2,
                    }
            elif current_hunk is not None:
                # Process lines within current hunk
                self._add_line_to_hunk(current_hunk, line, line_i, patch_lines)

        # Add last hunk
        if current_hunk is not None:
            hunks.append(current_hunk)

        return hunks

    def _add_line_to_hunk(
        self,
        hunk: Dict,
        line: str,
        line_i: int,
        patch_lines: List[str],
    ) -> None:
        """Add a line to the current hunk.

        Args:
            hunk: Current hunk dictionary to update
            line: Line to add
            line_i: Line index in patch
            patch_lines: All patch lines (for lookahead)
        """
        if line.startswith("+"):
            hunk["new_lines"].append(line)
        elif line.startswith("-"):
            hunk["old_lines"].append(line)
        else:
            # Skip empty lines before hunk headers or at end of patch
            if not line and line_i:
                if line_i + 1 < len(patch_lines) and patch_lines[line_i + 1].startswith(
                    "@@"
                ):
                    return
                elif line_i + 1 == len(patch_lines):
                    return

            # Context line (appears in both new and old)
            hunk["new_lines"].append(line)
            hunk["old_lines"].append(line)

    def _format_hunk_with_line_numbers(self, hunk: Dict) -> str:
        """Format a hunk with line numbers.

        Args:
            hunk: Hunk dictionary with header, new_lines, old_lines, start positions

        Returns:
            str: Formatted hunk string with line numbers
        """
        output = f"\n{hunk['header']}\n"

        # Check if there are any actual changes
        has_additions = any(line.startswith("+") for line in hunk["new_lines"])
        has_deletions = any(line.startswith("-") for line in hunk["old_lines"])

        if not (has_additions or has_deletions):
            return ""  # No changes in this hunk

        # Format new content section
        output = output.rstrip() + "\n__new hunk__\n"
        for i, line_new in enumerate(hunk["new_lines"]):
            output += f"{hunk['start2'] + i} {line_new}\n"

        # Format old content section if there are deletions
        if has_deletions:
            output = output.rstrip() + "\n__old hunk__\n"
            for line_old in hunk["old_lines"]:
                output += f"{line_old}\n"

        return output

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
            commit_messages_str = "\n".join(
                [f"{i + 1}. {message}" for i, message in enumerate(commit_messages)]
            )
        except Exception:
            commit_messages_str = ""
        return commit_messages_str

    def _process_single_file_for_diff(
        self, indexed_file_data: tuple
    ) -> Optional[tuple]:
        """Process a single file for diff generation (worker function for parallel processing).

        Args:
            indexed_file_data: Tuple of (index, file, add_line_numbers_to_hunks, total_files)

        Returns:
            Optional[tuple]: (index, extended_patch_string) or None if processing fails
        """
        i, file, add_line_numbers_to_hunks, total_files = indexed_file_data

        try:
            original_file_content_str = file.base_file
            new_file_content_str = file.head_file
            patch = file.patch

            if not patch:
                return None

            # Extend each patch with extra lines of context
            extended_patch = self._diff_utils.extend_patch(
                original_file_content_str, patch, new_file_str=new_file_content_str
            )

            if not extended_patch:
                self._logger.warning(
                    f"Failed to extend patch for file: {file.filename}"
                )
                return None

            is_first_file = (i == 0)

            if add_line_numbers_to_hunks:
                full_extended_patch = (
                    self._decouple_and_convert_to_hunks_with_lines_numbers(
                        extended_patch, file, is_first_file=is_first_file
                    )
                )
            else:
                # Add separator and file header
                separator = "" if is_first_file else "\n---"
                full_extended_patch = f"{separator}{"" if is_first_file else "\n\n"}## File: '{file.filename.strip()}'\n{extended_patch.rstrip()}\n"
                if is_first_file:
                    full_extended_patch = f"\n{full_extended_patch}"

            return (i, full_extended_patch)

        except Exception as e:
            self._logger.error(
                f"Error processing file {file.filename} in parallel: {e}"
            )
            return None

    def _generate_extended_diff_sequential(
        self, diff_files: List[FilePatchInfo], add_line_numbers_to_hunks: bool = False
    ) -> List[str]:
        """Generate extended diff using sequential processing.

        This is the original implementation that processes files one by one.

        Args:
            diff_files: List of FilePatchInfo objects to process
            add_line_numbers_to_hunks: Whether to add line numbers to hunks

        Returns:
            List of extended diff strings, one per file
        """
        extended_diffs = []
        for i, file in enumerate(diff_files):
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
                self._logger.warning(
                    f"Failed to extend patch for file: {file.filename}"
                )
                continue

            if add_line_numbers_to_hunks:
                full_extended_patch = (
                    self._decouple_and_convert_to_hunks_with_lines_numbers(
                        extended_patch, file, is_first_file=(i == 0)
                    )
                )
            else:
                # Add separator and file header
                separator = "" if i == 0 else "\n---"
                full_extended_patch = f"{separator}{"" if i == 0 else "\n\n"}## File: '{file.filename.strip()}'\n{extended_patch.rstrip()}\n"
                if i == 0:
                    full_extended_patch = f"\n{full_extended_patch}"
            extended_diffs.append(full_extended_patch)
        return extended_diffs

    def _generate_extended_diff_parallel(
        self, diff_files: List[FilePatchInfo], add_line_numbers_to_hunks: bool = False
    ) -> List[str]:
        """Generate extended diff using parallel processing.

        This implementation uses ParallelExecutor to process files concurrently,
        significantly improving performance for PRs with many files.

        Args:
            diff_files: List of FilePatchInfo objects to process
            add_line_numbers_to_hunks: Whether to add line numbers to hunks

        Returns:
            List of extended diff strings, one per file (in original order)
        """
        if not self._parallel_executor:
            # Fallback to sequential if no executor available
            self._logger.warning(
                "Parallel executor not available, falling back to sequential processing"
            )
            return self._generate_extended_diff_sequential(
                diff_files, add_line_numbers_to_hunks
            )

        start_time = time.time()
        total_files = len(diff_files)

        # Prepare data for parallel processing: (index, file, add_line_numbers, total_files)
        indexed_files = [
            (i, file, add_line_numbers_to_hunks, total_files)
            for i, file in enumerate(diff_files)
        ]

        self._logger.info(
            f"Starting parallel diff generation for {total_files} files using "
            f"{self._parallel_executor.max_workers} workers"
        )

        # Process all files in parallel
        results = self._parallel_executor.execute_batch(
            self._process_single_file_for_diff, indexed_files
        )

        # Filter out None results and sort by index to preserve original order
        valid_results = [r for r in results if r is not None]
        valid_results.sort(key=lambda x: x[0])

        # Extract just the patch strings (drop the index)
        extended_diffs = [patch for _, patch in valid_results]

        elapsed_time = time.time() - start_time
        self._logger.info(
            f"Parallel diff generation completed: {len(extended_diffs)}/{total_files} files "
            f"processed in {elapsed_time:.2f}s "
            f"({elapsed_time/total_files*1000:.1f}ms per file avg)"
        )

        return extended_diffs


def get_diff_generator(
    diff_utils: DiffServiceInterface,
    parallel_executor=None,
    parallel_enabled: bool = True,
    parallel_threshold: int = 3,
) -> DiffGenerator:
    """Get a configured diff generator instance.

    Args:
        diff_utils: Service for diff utilities
        parallel_executor: Optional parallel executor for concurrent processing
        parallel_enabled: Whether to use parallel processing (default: True)
        parallel_threshold: Minimum number of files to trigger parallel processing (default: 3)

    Returns:
        DiffGenerator: Configured diff generator instance
    """
    return DiffGenerator(
        diff_utils=diff_utils,
        parallel_executor=parallel_executor,
        parallel_enabled=parallel_enabled,
        parallel_threshold=parallel_threshold,
    )
