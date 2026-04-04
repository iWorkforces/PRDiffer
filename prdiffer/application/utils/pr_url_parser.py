"""Shared utility for parsing GitHub PR URLs.

Consolidates URL parsing for FastMCPServer and PROperationHandler.
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

    Args:
        pr_url: The GitHub pull request URL to parse
        input_validator: Optional InputValidator instance. If None, creates one.

    Returns:
        tuple[str, str, int]: (repo_owner, repo_name, pr_number)

    Raises:
        InvalidURLError: If the URL format is invalid, contains invalid characters,
            or is empty/whitespace-only, or not a string
        SuspiciousOperationError: If the URL contains suspicious patterns
        InvalidRepositoryError: If repository name is invalid
        InvalidPRNumberError: If PR number is invalid

    Examples:
        >>> parse_pr_url("https://github.com/owner/repo/pull/123")
        ('owner', 'repo', 123)

        >>> parse_pr_url("https://github.com/owner/repo/pulls/456")
        ('owner', 'repo', 456)
    """
    if not isinstance(pr_url, str):
        raise InvalidURLError(f"PR URL must be a string, got {type(pr_url).__name__}")

    pr_url_stripped = pr_url.strip()
    if not pr_url_stripped:
        raise InvalidURLError("PR URL cannot be empty or whitespace-only")

    validator = input_validator or InputValidator()
    return validator.validate_github_url(pr_url_stripped)
