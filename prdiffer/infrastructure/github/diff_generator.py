"""Diff generation and patch processing service."""

import re
import time
from prdiffer.domain.entities.file_patch import FilePatchInfo
from prdiffer.domain.services import DiffServiceInterface
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)


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

    def generate_extended_diff(self, diff_files: list[FilePatchInfo], add_line_numbers_to_hunks: bool = False) -> list[str]:
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
        use_parallel = self._parallel_enabled and num_files >= self._parallel_threshold and self._parallel_executor is not None

        if use_parallel:
            self._logger.debug(f"Using parallel processing for {num_files} files (threshold: {self._parallel_threshold})")
            return self._generate_extended_diff_parallel(diff_files, add_line_numbers_to_hunks)
        else:
            reason = "disabled" if not self._parallel_enabled else f"below threshold ({num_files} < {self._parallel_threshold})"
            self._logger.debug(f"Using sequential processing for {num_files} files (parallel {reason})")
            return self._generate_extended_diff_sequential(diff_files, add_line_numbers_to_hunks)

    def _decouple_and_convert_to_hunks_with_lines_numbers(self, patch: str, file: FilePatchInfo, is_first_file: bool = False) -> str:
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

        # Process all hunks in the patch
        patch_lines = patch.splitlines()
        hunks = self._parse_hunks_from_patch(patch_lines)

        # Format each hunk with line numbers
        for hunk in hunks:
            patch_with_lines_str += self._format_hunk_with_line_numbers(hunk)

        return patch_with_lines_str.rstrip()

    def _generate_file_header(self, file: FilePatchInfo | None, is_first_file: bool) -> str:
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

        return f"{separator}\n## Full file path: `{file.filename.strip()}`\n"

    def _parse_hunks_from_patch(self, patch_lines: list[str]) -> list[dict]:
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
                    section_header, size1, size2, start1, start2 = self._extract_hunk_headers(match)
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
        hunk: dict,
        line: str,
        line_i: int,
        patch_lines: list[str],
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
                if line_i + 1 < len(patch_lines) and patch_lines[line_i + 1].startswith("@@"):
                    return
                elif line_i + 1 == len(patch_lines):
                    return

            # Context line (appears in both new and old)
            hunk["new_lines"].append(line)
            hunk["old_lines"].append(line)

    def _format_hunk_with_line_numbers(self, hunk: dict) -> str:
        """Format a hunk with line numbers.

        Handles edge cases:
        - New files (start1=0): Uses start2 for line numbers
        - Files with only deletions: Shows old content appropriately
        - Empty hunks: Returns empty string
        - No newline at EOF: Already filtered in _add_line_to_hunk

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

        # Handle deletion-only case (file deleted or only lines removed)
        is_deletion_only = has_deletions and not has_additions

        # Calculate starting line number for new content
        # For new files with start2=0, use 1 as the starting line
        new_start_line = max(1, hunk["start2"])

        # Format new content section (unless deletion-only)
        if not is_deletion_only:
            output = output.rstrip() + "\n__new hunk__\n"
            line_num = new_start_line
            new_lines_output = []
            for line_new in hunk["new_lines"]:
                # Skip deleted lines in new hunk display
                if not line_new.startswith("-"):
                    new_lines_output.append(f"{line_num} {line_new}")
                    line_num += 1
            output += "\n".join(new_lines_output)
            if new_lines_output:
                output += "\n"
        elif is_deletion_only and hunk["new_lines"]:
            # Show context lines even for deletion-only hunks
            output = output.rstrip() + "\n__new hunk__\n"
            line_num = new_start_line
            new_lines_output = []
            for line_new in hunk["new_lines"]:
                if not line_new.startswith("-"):
                    new_lines_output.append(f"{line_num} {line_new}")
                    line_num += 1
            output += "\n".join(new_lines_output)
            if new_lines_output:
                output += "\n"

        # Format old content section if there are deletions
        if has_deletions:
            output = output.rstrip() + "\n__old hunk__\n"
            # Calculate starting line number for old content
            # For new files, there's no old content to number
            old_start_line = max(1, hunk["start1"])
            line_num = old_start_line
            old_lines_output = []
            for line_old in hunk["old_lines"]:
                # Add line numbers to old hunk for better context
                old_lines_output.append(f"{line_num} {line_old}")
                line_num += 1
            output += "\n".join(old_lines_output)
            if old_lines_output:
                output += "\n"

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
            Handles edge cases:
            - '@@ -0,0 +1 @@' for new files (no original content)
            - '@@ -1 +0,0 @@' for deleted files (no new content)
            - '@@ -1,3 +1,3 @@' for standard modifications
            - Missing size values default to 1
        """
        res = list(match.groups())

        # Convert None values to appropriate defaults
        # Groups: (start1, size1, start2, size2, section_header)
        # Pattern: @@ -(start1)(?:,(size1))? +(start2)(?:,(size2))? @@
        for i in range(4):  # Only process numeric fields
            if res[i] is None:
                # Size defaults to 1 if not specified (e.g., @@ -1 +1 @@)
                res[i] = "1" if i in (1, 3) else "0"

        try:
            start1 = int(res[0])
            size1 = int(res[1])
            start2 = int(res[2])
            size2 = int(res[3])
        except (ValueError, IndexError) as e:
            # Fallback for unexpected formats
            self._logger.warning(f"Unexpected hunk header format: {e}")
            start1, size1, start2, size2 = 0, 0, 0, 0

        section_header = res[4] if len(res) > 4 else ""
        return section_header, size1, size2, start1, start2

    def _process_single_file_for_diff(self, indexed_file_data: tuple) -> tuple | None:
        """Process a single file for diff generation (worker function for parallel processing).

        Args:
            indexed_file_data: Tuple of (index, file, add_line_numbers_to_hunks, total_files)

        Returns:
            tuple | None: (index, extended_patch_string) or None if processing fails
        """
        i, file, add_line_numbers_to_hunks, total_files = indexed_file_data

        try:
            original_file_content_str = file.base_file
            new_file_content_str = file.head_file
            patch = file.patch

            if not patch:
                return None

            # Extend each patch with extra lines of context
            extended_patch = self._diff_utils.extend_patch(original_file_content_str, patch, new_file_str=new_file_content_str)

            if not extended_patch:
                self._logger.warning(f"Failed to extend patch for file: {file.filename}")
                return None

            is_first_file = i == 0

            if add_line_numbers_to_hunks:
                full_extended_patch = self._decouple_and_convert_to_hunks_with_lines_numbers(extended_patch, file, is_first_file=is_first_file)
            else:
                # Add separator and file header
                separator = "" if is_first_file else "\n---"
                full_extended_patch = f"{separator}{'' if is_first_file else '\n\n'}## Full file path: `{file.filename.strip()}`\n{extended_patch.rstrip()}\n"
                if is_first_file:
                    full_extended_patch = f"\n{full_extended_patch}"

            return (i, full_extended_patch)

        except Exception as e:
            sanitized = sanitize_exception_for_logging(e)
            self._logger.error(f"Error processing file {file.filename} in parallel", extra=sanitized)
            return None

    def _generate_extended_diff_sequential(self, diff_files: list[FilePatchInfo], add_line_numbers_to_hunks: bool = False) -> list[str]:
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
            extended_patch = self._diff_utils.extend_patch(original_file_content_str, patch, new_file_str=new_file_content_str)
            if not extended_patch:
                self._logger.warning(f"Failed to extend patch for file: {file.filename}")
                continue

            if add_line_numbers_to_hunks:
                full_extended_patch = self._decouple_and_convert_to_hunks_with_lines_numbers(extended_patch, file, is_first_file=(i == 0))
            else:
                # Add separator and file header
                separator = "" if i == 0 else "\n---"
                full_extended_patch = f"{separator}{'' if i == 0 else '\n\n'}## Full file path: `{file.filename.strip()}`\n{extended_patch.rstrip()}\n"
                if i == 0:
                    full_extended_patch = f"\n{full_extended_patch}"
            extended_diffs.append(full_extended_patch)
        return extended_diffs

    def _generate_extended_diff_parallel(self, diff_files: list[FilePatchInfo], add_line_numbers_to_hunks: bool = False) -> list[str]:
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
            self._logger.warning("Parallel executor not available, falling back to sequential processing")
            return self._generate_extended_diff_sequential(diff_files, add_line_numbers_to_hunks)

        start_time = time.time()
        total_files = len(diff_files)

        # Prepare data for parallel processing: (index, file, add_line_numbers, total_files)
        indexed_files = [(i, file, add_line_numbers_to_hunks, total_files) for i, file in enumerate(diff_files)]

        self._logger.info(f"Starting parallel diff generation for {total_files} files using {self._parallel_executor.max_workers} workers")

        # Process all files in parallel
        results = self._parallel_executor.execute_batch(self._process_single_file_for_diff, indexed_files)

        # Filter out None results and sort by index to preserve original order
        valid_results = [r for r in results if r is not None]
        valid_results.sort(key=lambda x: x[0])

        # Extract just the patch strings (drop the index)
        extended_diffs = [patch for _, patch in valid_results]

        elapsed_time = time.time() - start_time
        self._logger.info(
            f"Parallel diff generation completed: {len(extended_diffs)}/{total_files} files "
            f"processed in {elapsed_time:.2f}s "
            f"({elapsed_time / total_files * 1000:.1f}ms per file avg)"
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
