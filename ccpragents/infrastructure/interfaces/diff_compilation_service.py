"""Infrastructure interface for diff compilation operations.

This interface defines the contract for compiling and formatting diffs
at the infrastructure layer.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from ccpragents.domain.entities.file_patch import FilePatchInfo


class DiffCompilationServiceInterface(ABC):
    """Abstract interface for diff compilation operations."""

    @abstractmethod
    def compile_pr_diff(
        self,
        repository_name: str,
        pr_number: int,
        files: List[FilePatchInfo],
        commit_messages: Optional[List[str]] = None,
        pr_title: Optional[str] = None,
        pr_body: Optional[str] = None,
    ) -> str:
        """Compile a complete PR diff from file patches.

        Args:
            repository_name: Repository name in format "owner/repo"
            pr_number: Pull request number
            files: List of file patches
            commit_messages: Optional list of commit messages
            pr_title: Optional PR title
            pr_body: Optional PR body

        Returns:
            str: Complete formatted PR diff

        Raises:
            CompilationError: If diff compilation fails
        """
        pass

    @abstractmethod
    def format_file_diff(self, file_patch: FilePatchInfo) -> str:
        """Format a single file patch for output.

        Args:
            file_patch: FilePatchInfo instance

        Returns:
            str: Formatted file diff string

        Raises:
            FormattingError: If formatting fails
        """
        pass

    @abstractmethod
    def add_line_numbers(self, diff_content: str) -> str:
        """Add line numbers to diff content.

        Args:
            diff_content: Raw diff content

        Returns:
            str: Diff content with line numbers

        Raises:
            FormattingError: If line number addition fails
        """
        pass

    @abstractmethod
    def generate_diff_summary(
        self,
        repository_name: str,
        pr_number: int,
        files: List[FilePatchInfo],
        stats_only: bool = False,
    ) -> Dict[str, any]:
        """Generate a summary of the diff.

        Args:
            repository_name: Repository name in format "owner/repo"
            pr_number: Pull request number
            files: List of file patches
            stats_only: If True, only include statistics

        Returns:
            Dict[str, any]: Diff summary with statistics and metadata

        Raises:
            CompilationError: If summary generation fails
        """
        pass

    @abstractmethod
    def validate_diff_format(self, diff_content: str) -> bool:
        """Validate that diff content is in proper format.

        Args:
            diff_content: Diff content to validate

        Returns:
            bool: True if diff is properly formatted, False otherwise
        """
        pass

    @abstractmethod
    def optimize_diff_size(self, diff_content: str, max_size: int) -> str:
        """Optimize diff content to fit within size limits.

        Args:
            diff_content: Original diff content
            max_size: Maximum allowed size in characters

        Returns:
            str: Optimized diff content within size limits

        Raises:
            OptimizationError: If optimization fails
        """
        pass

    @abstractmethod
    def extract_changed_lines(
        self, file_patch: FilePatchInfo, context_lines: int = 3
    ) -> List[str]:
        """Extract changed lines with context from a file patch.

        Args:
            file_patch: FilePatchInfo instance
            context_lines: Number of context lines to include

        Returns:
            List[str]: List of changed lines with context

        Raises:
            ExtractionError: If line extraction fails
        """
        pass
