"""Diff generation and patch processing service."""

import re
import time
import logging
from typing import Any, TypedDict
from prdiffer.domain.entities.file_patch import FilePatchInfo
from prdiffer.domain.services.diff import DiffServiceInterface
from prdiffer.infrastructure.logging.console_logger import get_logger
from prdiffer.infrastructure.logging.exception_utils import (
    sanitize_exception_for_logging,
)


class HunkDict(TypedDict):
    """Typed dictionary for a parsed patch hunk."""

    header: str
    new_lines: list[str]
    old_lines: list[str]
    start1: int
    start2: int


class DiffGenerator:
    """Service for generating extended diffs and processing patches."""

    RE_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[ ]?(.*)")

    def __init__(
        self,
        diff_utils: DiffServiceInterface,
        parallel_executor: Any = None,
        parallel_enabled: bool = True,
        parallel_threshold: int = 3,
        logger: logging.Logger | None = None,
    ) -> None:
        self._diff_utils = diff_utils
        self._parallel_executor = parallel_executor
        self._parallel_enabled = parallel_enabled and parallel_executor is not None
        self._parallel_threshold = parallel_threshold
        self._logger = logger or get_logger()

    def generate_extended_diff(self, diff_files: list[FilePatchInfo], add_line_numbers_to_hunks: bool = False) -> list[str]:
        """Generate an extended diff for a pull request."""
        num_files = len(diff_files)

        use_parallel = self._parallel_enabled and num_files >= self._parallel_threshold and self._parallel_executor is not None

        if use_parallel:
            self._logger.debug(f"Using parallel processing for {num_files} files (threshold: {self._parallel_threshold})")
            return self._generate_extended_diff_parallel(diff_files, add_line_numbers_to_hunks)
        else:
            reason = "disabled" if not self._parallel_enabled else f"below threshold ({num_files} < {self._parallel_threshold})"
            self._logger.debug(f"Using sequential processing for {num_files} files (parallel {reason})")
            return self._generate_extended_diff_sequential(diff_files, add_line_numbers_to_hunks)

    def _decouple_and_convert_to_hunks_with_lines_numbers(self, patch: str, file: FilePatchInfo, is_first_file: bool = False) -> str:
        """Convert a given patch string into a string with line numbers for each hunk."""
        patch_with_lines_str = self._generate_file_header(file, is_first_file)

        patch_lines = patch.splitlines()
        hunks = self._parse_hunks_from_patch(patch_lines)

        for hunk in hunks:
            patch_with_lines_str += self._format_hunk_with_line_numbers(hunk)

        return patch_with_lines_str.rstrip()

    def _generate_file_header(self, file: FilePatchInfo | None, is_first_file: bool) -> str:
        """Generate the file header for the patch output."""
        if not file:
            return ""

        separator = "" if is_first_file else "\n\n---"

        return f"{separator}\n## Full file path: `{file.filename.strip()}`\n"

    def _parse_hunks_from_patch(self, patch_lines: list[str]) -> list[HunkDict]:
        """Parse hunks from patch lines."""
        hunks: list[HunkDict] = []
        current_hunk: HunkDict | None = None
        RE_HUNK_HEADER = self.RE_HUNK_HEADER

        for line_i, line in enumerate(patch_lines):
            if "no newline at end of file" in line.lower():
                continue

            if line.startswith("@@"):
                if current_hunk is not None:
                    hunks.append(current_hunk)

                match = RE_HUNK_HEADER.match(line)
                if match:
                    _, _, _, start1, start2 = self._extract_hunk_headers(match)
                    current_hunk = {
                        "header": line,
                        "new_lines": [],
                        "old_lines": [],
                        "start1": start1,
                        "start2": start2,
                    }
            elif current_hunk is not None:
                self._add_line_to_hunk(current_hunk, line, line_i, patch_lines)

        if current_hunk is not None:
            hunks.append(current_hunk)

        return hunks

    def _add_line_to_hunk(
        self,
        hunk: HunkDict,
        line: str,
        line_i: int,
        patch_lines: list[str],
    ) -> None:
        """Add a line to the current hunk."""
        if line.startswith("+"):
            hunk["new_lines"].append(line)
        elif line.startswith("-"):
            hunk["old_lines"].append(line)
        else:
            if not line and line_i:
                if line_i + 1 < len(patch_lines) and patch_lines[line_i + 1].startswith("@@"):
                    return
                elif line_i + 1 == len(patch_lines):
                    return

            hunk["new_lines"].append(line)
            hunk["old_lines"].append(line)

    def _format_hunk_with_line_numbers(self, hunk: HunkDict) -> str:
        """Format a hunk with line numbers.

        Handles edge cases:
        - New files (start1=0): Uses start2 for line numbers
        - Files with only deletions: Shows old content appropriately
        - Empty hunks: Returns empty string
        """
        output = f"\n{hunk['header']}\n"

        has_additions = any(line.startswith("+") for line in hunk["new_lines"])
        has_deletions = any(line.startswith("-") for line in hunk["old_lines"])

        if not (has_additions or has_deletions):
            return ""  # No changes in this hunk

        is_deletion_only = has_deletions and not has_additions

        new_start_line = max(1, hunk["start2"])

        if not is_deletion_only:
            output = output.rstrip() + "\n__new hunk__\n"
            line_num = new_start_line
            new_lines_output: list[str] = []
            for line_new in hunk["new_lines"]:
                if not line_new.startswith("-"):
                    new_lines_output.append(f"{line_num} {line_new}")
                    line_num += 1
            output += "\n".join(new_lines_output)
            if new_lines_output:
                output += "\n"
        elif is_deletion_only and hunk["new_lines"]:
            output = output.rstrip() + "\n__new hunk__\n"
            line_num = new_start_line
            new_lines_output: list[str] = []
            for line_new in hunk["new_lines"]:
                if not line_new.startswith("-"):
                    new_lines_output.append(f"{line_num} {line_new}")
                    line_num += 1
            output += "\n".join(new_lines_output)
            if new_lines_output:
                output += "\n"

        if has_deletions:
            output = output.rstrip() + "\n__old hunk__\n"
            old_start_line = max(1, hunk["start1"])
            line_num = old_start_line
            old_lines_output: list[str] = []
            for line_old in hunk["old_lines"]:
                old_lines_output.append(f"{line_num} {line_old}")
                line_num += 1
            output += "\n".join(old_lines_output)
            if old_lines_output:
                output += "\n"

        return output

    def _extract_hunk_headers(self, match: re.Match[str]) -> tuple[str, int, int, int, int]:
        """Extract and parse hunk header information from regex match.

        Note:
            Handles edge cases:
            - '@@ -0,0 +1 @@' for new files (no original content)
            - '@@ -1 +0,0 @@' for deleted files (no new content)
            - '@@ -1,3 +1,3 @@' for standard modifications
            - Missing size values default to 1
        """
        res: list[str | None] = list(match.groups())

        # Groups: (start1, size1, start2, size2, section_header)
        # Pattern: @@ -(start1)(?:,(size1))? +(start2)(?:,(size2))? @@
        for i in range(4):  # Only process numeric fields
            if res[i] is None:
                res[i] = "1" if i in (1, 3) else "0"

        try:
            start1 = int(res[0] or "0")
            size1 = int(res[1] or "1")
            start2 = int(res[2] or "0")
            size2 = int(res[3] or "1")
        except (ValueError, IndexError) as e:
            self._logger.warning(f"Unexpected hunk header format: {e}")
            start1, size1, start2, size2 = 0, 0, 0, 0

        section_header: str = res[4] if len(res) > 4 and res[4] is not None else ""
        return section_header, size1, size2, start1, start2

    def _process_single_file_for_diff(self, indexed_file_data: tuple[int, FilePatchInfo, bool, int]) -> tuple[int, str] | None:
        """Process a single file for diff generation (worker function for parallel processing)."""
        i, file, add_line_numbers_to_hunks, _total_files = indexed_file_data

        try:
            original_file_content_str = file.base_file
            new_file_content_str = file.head_file
            patch = file.patch

            if not patch:
                return None

            extended_patch = self._diff_utils.extend_patch(original_file_content_str, patch, new_file_str=new_file_content_str)

            if not extended_patch:
                self._logger.warning(f"Failed to extend patch for file: {file.filename}")
                return None

            is_first_file = i == 0

            if add_line_numbers_to_hunks:
                full_extended_patch = self._decouple_and_convert_to_hunks_with_lines_numbers(extended_patch, file, is_first_file=is_first_file)
            else:
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
        """Generate extended diff using sequential processing."""
        extended_diffs: list[str] = []
        for i, file in enumerate(diff_files):
            original_file_content_str = file.base_file
            new_file_content_str = file.head_file
            patch = file.patch
            if not patch:
                continue

            extended_patch = self._diff_utils.extend_patch(original_file_content_str, patch, new_file_str=new_file_content_str)
            if not extended_patch:
                self._logger.warning(f"Failed to extend patch for file: {file.filename}")
                continue

            if add_line_numbers_to_hunks:
                full_extended_patch = self._decouple_and_convert_to_hunks_with_lines_numbers(extended_patch, file, is_first_file=(i == 0))
            else:
                separator = "" if i == 0 else "\n---"
                full_extended_patch = f"{separator}{'' if i == 0 else '\n\n'}## Full file path: `{file.filename.strip()}`\n{extended_patch.rstrip()}\n"
                if i == 0:
                    full_extended_patch = f"\n{full_extended_patch}"
            extended_diffs.append(full_extended_patch)
        return extended_diffs

    def _generate_extended_diff_parallel(self, diff_files: list[FilePatchInfo], add_line_numbers_to_hunks: bool = False) -> list[str]:
        """Generate extended diff using parallel processing.

        Uses ParallelExecutor to process files concurrently,
        improving performance for PRs with many files.
        """
        if not self._parallel_executor:
            self._logger.warning("Parallel executor not available, falling back to sequential processing")
            return self._generate_extended_diff_sequential(diff_files, add_line_numbers_to_hunks)

        start_time = time.time()
        total_files = len(diff_files)

        indexed_files = [(i, file, add_line_numbers_to_hunks, total_files) for i, file in enumerate(diff_files)]

        self._logger.info(f"Starting parallel diff generation for {total_files} files using {self._parallel_executor.max_workers} workers")

        results = self._parallel_executor.execute_batch(self._process_single_file_for_diff, indexed_files)

        valid_results = [r for r in results if r is not None]
        valid_results.sort(key=lambda x: x[0])

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
    parallel_executor: Any = None,
    parallel_enabled: bool = True,
    parallel_threshold: int = 3,
) -> DiffGenerator:
    """Get a configured diff generator instance."""
    return DiffGenerator(
        diff_utils=diff_utils,
        parallel_executor=parallel_executor,
        parallel_enabled=parallel_enabled,
        parallel_threshold=parallel_threshold,
    )
