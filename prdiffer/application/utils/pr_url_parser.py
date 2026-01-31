"""Shared utility for parsing GitHub PR URLs.

This module provides a centralized function for parsing GitHub pull request URLs
and extracting repository owner, name, and PR number. Used by both FastMCPServer
and PROperationHandler to avoid code duplication.
"""

from prdiffer.domain.exceptions import (
    InvalidURLError,
)
from prdiffer.infrastructure.security.input_validator import InputValidator


def parse_pr_url(
    pr_url: str,
    input_validator: InputValidator | None = None,
) -> tuple[str, str, int]:
    """Parse GitHub PR URL to extract repository owner, name, and PR number.

    This is a shared utility that consolidates URL parsing logic across the
    application layer. It uses InputValidator for comprehensive validation
    including injection detection and format validation.

    Args:
        pr_url: The GitHub pull request URL to parse
        input_validator: Optional InputValidator instance. If None, creates one.

    Returns:
        tuple[str, str, int]: A tuple containing (repo_owner, repo_name, pr_number)

    Raises:
        InvalidURLError: If the URL format is invalid, contains invalid characters,
            or is empty/whitespace-only
        SuspiciousOperationError: If the URL contains suspicious patterns
        InvalidRepositoryError: If repository name is invalid
        InvalidPRNumberError: If PR number is invalid

    Examples:
        >>> parse_pr_url("https://github.com/owner/repo/pull/123")
        ('owner', 'repo', 123)

        >>> parse_pr_url("https://github.com/owner/repo/pulls/456")
        ('owner', 'repo', 456)
    """
    # Validate input is not None or empty before processing
    if pr_url is None:
        raise InvalidURLError("PR URL cannot be None")

    if not isinstance(pr_url, str):
        raise InvalidURLError(f"PR URL must be a string, got {type(pr_url).__name__}")

    pr_url_stripped = pr_url.strip()
    if not pr_url_stripped:
        raise InvalidURLError("PR URL cannot be empty or whitespace-only")

    # Delegate to input validator for full validation
    validator = input_validator or InputValidator()
    return validator.validate_github_url(pr_url_stripped)
