"""Protocol definition for input validation and sanitization.

This module defines the InputValidatorProtocol that infrastructure
implementations must satisfy, following Clean Architecture principles.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class InputValidatorProtocol(Protocol):
    """Protocol for input validation and sanitization.

    Defines the contract for validating and sanitizing user inputs
    to prevent injection attacks, path traversal, and other security threats.
    """

    def validate_github_url(self, url: str) -> tuple[str, str, int]:
        """Validate and parse a GitHub PR URL.

        Args:
            url: GitHub PR URL to validate

        Returns:
            Tuple of (owner, repo, pr_number)
        """
        ...

    def validate_gitlab_url(self, url: str) -> tuple[str, str, int]:
        """Validate and parse a canonical GitLab merge request URL."""
        ...

    def validate_repository_identifier(self, identifier: str) -> tuple[str, str]:
        """Validate a repository identifier (owner/repo format).

        Args:
            identifier: Repository identifier to validate

        Returns:
            Tuple of (owner, repo)
        """
        ...

    def sanitize_string(self, value: str, max_length: int = 1000) -> str:
        """Sanitize a string input.

        Args:
            value: String to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string
        """
        ...

    def validate_pr_number(self, pr_number: int) -> int:
        """Validate a PR number.

        Args:
            pr_number: PR number to validate

        Returns:
            Validated PR number
        """
        ...

    def validate_file_path(self, file_path: str) -> str:
        """Validate a file path for safe operations.

        Args:
            file_path: File path to validate

        Returns:
            Validated file path
        """
        ...

    def validate_token(self, token: str) -> str:
        """Validate an authentication token format.

        Args:
            token: Token to validate

        Returns:
            Validated token
        """
        ...

    def validate_user_id(self, user_id: str) -> str:
        """Validate a user ID.

        Args:
            user_id: User ID to validate

        Returns:
            Validated user ID
        """
        ...

    def validate_branch_name(self, branch: str) -> str:
        """Validate a Git branch or reference name.

        Args:
            branch: Branch or reference name to validate

        Returns:
            Validated branch name
        """
        ...

    def sanitize_for_logging(self, value: str, max_length: int = 200) -> str:
        """Sanitize a value for safe logging.

        Args:
            value: Value to sanitize
            max_length: Maximum length for logged value

        Returns:
            Sanitized value safe for logging
        """
        ...
