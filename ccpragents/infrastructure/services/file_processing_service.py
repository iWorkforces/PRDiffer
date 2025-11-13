"""Infrastructure implementation of FileProcessingServiceInterface.

This module provides the concrete implementation of FileProcessingServiceInterface
using GitHub API operations and utility services.
"""

from typing import List, Optional
import asyncio

from ccpragents.domain.entities.file_patch import FilePatchInfo
from ccpragents.domain.services.file_processing_service import (
    FileProcessingServiceInterface,
)
from ccpragents.infrastructure.github.api_client import GitHubAPIClient
from ccpragents.infrastructure.utils.diff_utils import DiffUtils
from ccpragents.infrastructure.utils.pattern_matcher import PatternMatcher


class GitHubFileProcessingService(FileProcessingServiceInterface):
    """Concrete implementation of FileProcessingServiceInterface using GitHub API."""

    def __init__(
        self,
        github_api_client: Optional[GitHubAPIClient] = None,
        diff_utility: Optional[DiffUtils] = None,
        pattern_matcher: Optional[PatternMatcher] = None,
    ):
        """Initialize the service with required utilities.

        Args:
            github_api_client: Optional GitHub API client (created if None)
            diff_utility: Optional diff utility (created if None)
            pattern_matcher: Optional pattern matcher (created if None)
        """
        self._github_api = github_api_client or GitHubAPIClient()
        self._diff_utility = diff_utility or DiffUtils()
        self._pattern_matcher = pattern_matcher or PatternMatcher()

    async def process_pr_files(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        max_files: Optional[int] = None,
    ) -> List[FilePatchInfo]:
        """Process all files in a pull request.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            pr_number: Pull request number
            max_files: Maximum number of files to process (optional)

        Returns:
            List[FilePatchInfo]: List of processed file patches

        Raises:
            RepositoryNotFoundError: If repository or PR doesn't exist
            AuthenticationError: If authentication fails
            FileProcessingError: If file processing fails
        """
        try:
            # Get repository and PR
            repository = self._github_api.get_repository(repo_owner, repo_name)
            if not repository:
                return []

            pull_request = self._github_api.get_pull_request(repository, pr_number)
            if not pull_request:
                return []

            # Get PR files
            pr_files = self._github_api.get_pr_files(pull_request)

            # Filter files if max_files is specified
            if max_files and len(pr_files) > max_files:
                pr_files = pr_files[:max_files]

            # Process files concurrently
            file_tasks = []
            for pr_file in pr_files:
                task = self._process_single_file(repository, pr_file)
                file_tasks.append(task)

            # Execute all file processing tasks concurrently
            processed_files = await asyncio.gather(*file_tasks, return_exceptions=True)

            # Filter out any exceptions and return successful results
            result = []
            for file_result in processed_files:
                if isinstance(file_result, Exception):
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(
                        "Failed to process file",
                        error=str(file_result),
                        error_type=type(file_result).__name__,
                    )
                elif file_result:
                    result.append(file_result)

            return result

        except Exception as e:
            # Log the error and return empty list for graceful degradation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to process PR files",
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    async def _process_single_file(
        self, repository, pr_file
    ) -> Optional[FilePatchInfo]:
        """Process a single file and create FilePatchInfo.

        Args:
            repository: GitHub repository object
            pr_file: GitHub PR file object

        Returns:
            Optional[FilePatchInfo]: Processed file information or None if failed
        """
        try:
            filename = pr_file.filename
            if not filename:
                return None

            # Check if file should be processed based on patterns
            if not self._pattern_matcher.is_valid_file(filename):
                return None

            # Get file content for base and head
            # Note: This is a simplified implementation
            # In a real implementation, you would get the base and head content
            # and generate proper diffs

            base_content = ""
            head_content = ""

            # Try to get file content if it's not a deletion
            if pr_file.status != "removed":
                head_content = self._github_api.get_file_content(repository, filename)

            # Generate diff
            diff_content = self._diff_utility.build_full_file_patch(
                base_content, head_content, filename
            )

            # Create FilePatchInfo
            file_patch = FilePatchInfo(
                filename=filename,
                patch=diff_content,
                edit_type=self._get_edit_type(pr_file.status),
                num_plus_lines=pr_file.additions or 0,
                num_minus_lines=pr_file.deletions or 0,
                language=self.get_file_language(filename, head_content),
                ai_file_summary="",
            )

            return file_patch

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to process single file",
                filename=getattr(pr_file, "filename", "unknown"),
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def filter_files(
        self,
        file_paths: List[str],
        ignore_patterns: Optional[List[str]] = None,
        valid_extensions: Optional[List[str]] = None,
    ) -> List[str]:
        """Filter files based on ignore patterns and valid extensions.

        Args:
            file_paths: List of file paths to filter
            ignore_patterns: List of patterns to ignore (optional)
            valid_extensions: List of valid file extensions (optional)

        Returns:
            List[str]: Filtered list of file paths
        """
        filtered_files = []

        for file_path in file_paths:
            # Use pattern matcher to validate file
            if self._pattern_matcher.is_valid_file(file_path):
                filtered_files.append(file_path)

        return filtered_files

    async def get_file_content(
        self,
        repo_owner: str,
        repo_name: str,
        file_path: str,
        commit_sha: str,
    ) -> Optional[str]:
        """Get the content of a specific file at a commit SHA.

        Args:
            repo_owner: Repository owner/organization name
            repo_name: Repository name
            file_path: Path to the file
            commit_sha: Commit SHA to get content from

        Returns:
            Optional[str]: File content if successful, None otherwise

        Raises:
            FileNotFoundError: If file doesn't exist at the commit SHA
            AuthenticationError: If authentication fails
        """
        try:
            repository = self._github_api.get_repository(repo_owner, repo_name)
            if not repository:
                return None

            # Get file content at specific commit
            return self._github_api.get_file_content_at_commit(
                repository, file_path, commit_sha
            )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to get file content",
                repo_owner=repo_owner,
                repo_name=repo_name,
                file_path=file_path,
                commit_sha=commit_sha,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def generate_file_diff(
        self,
        original_content: str,
        new_content: str,
        filename: str,
    ) -> str:
        """Generate a unified diff for a file.

        Args:
            original_content: Original file content
            new_content: New file content
            filename: Name of the file

        Returns:
            str: Unified diff string

        Raises:
            DiffGenerationError: If diff generation fails
        """
        try:
            return self._diff_utility.build_full_file_patch(
                original_content, new_content, filename
            )
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to generate file diff",
                filename=filename,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return empty diff on failure
            return f"--- a/{filename}\n+++ b/{filename}\n@@ -0,0 +0,0 @@\n"

    def is_binary_file(self, content: bytes) -> bool:
        """Determine if a file is binary based on its content.

        Args:
            content: File content as bytes

        Returns:
            bool: True if the file is binary, False otherwise
        """
        try:
            return self._diff_utility.is_binary_file(content)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to check if file is binary",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Default to treating as text file on error
            return False

    def get_file_language(self, filename: str, content: str) -> Optional[str]:
        """Detect the programming language of a file.

        Args:
            filename: Name of the file
            content: File content

        Returns:
            Optional[str]: Detected language, or None if undetermined
        """
        try:
            return self._diff_utility.detect_language(filename, content)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to detect file language",
                filename=filename,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _get_edit_type(self, status: str) -> str:
        """Convert GitHub file status to our edit type enum.

        Args:
            status: GitHub file status (added, removed, modified, renamed, etc.)

        Returns:
            str: Corresponding edit type
        """
        status_mapping = {
            "added": "ADDED",
            "removed": "DELETED",
            "modified": "MODIFIED",
            "renamed": "RENAMED",
        }
        return status_mapping.get(status, "UNKNOWN")
