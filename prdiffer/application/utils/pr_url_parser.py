"""Shared utility for parsing GitHub PR URLs.

Consolidates URL parsing for FastMCPServer and PROperationHandler.
"""

from dataclasses import dataclass
from typing import Literal

from prdiffer.domain.exceptions import (
    InvalidURLError,
)
from prdiffer.domain.interfaces.input_validation import InputValidatorProtocol


@dataclass(frozen=True, slots=True)
class PRTarget:
    """A validated pull or merge request target."""

    provider: Literal["github", "gitlab"]
    repo_owner: str
    repo_name: str
    pr_number: int


def parse_pr_url(
    pr_url: str,
    input_validator: InputValidatorProtocol | None = None,
) -> tuple[str, str, int]:
    """Parse GitHub PR URL to extract repository owner, name, and PR number.

    Args:
        pr_url: The GitHub pull request URL to parse
        input_validator: Optional InputValidatorProtocol instance. If None, creates one via factory.

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
    if input_validator is None:
        from prdiffer.infrastructure.factories.infrastructure_factory import get_infrastructure_factory

        input_validator = get_infrastructure_factory().create_input_validator()
    return input_validator.validate_github_url(pr_url_stripped)


def parse_pr_target(
    pr_url: str,
    input_validator: InputValidatorProtocol | None = None,
) -> PRTarget:
    """Parse a supported PR or merge request URL into a provider-aware target."""
    if not isinstance(pr_url, str):
        raise InvalidURLError(f"PR URL must be a string, got {type(pr_url).__name__}")

    pr_url_stripped = pr_url.strip()
    if not pr_url_stripped:
        raise InvalidURLError("PR URL cannot be empty or whitespace-only")
    if input_validator is None:
        from prdiffer.infrastructure.factories.infrastructure_factory import get_infrastructure_factory

        input_validator = get_infrastructure_factory().create_input_validator()

    if pr_url_stripped.startswith("https://github.com/"):
        repo_owner, repo_name, pr_number = parse_pr_url(pr_url_stripped, input_validator)
        return PRTarget("github", repo_owner, repo_name, pr_number)
    if pr_url_stripped.startswith("https://gitlab.com/"):
        repo_owner, repo_name, pr_number = input_validator.validate_gitlab_url(pr_url_stripped)
        return PRTarget("gitlab", repo_owner, repo_name, pr_number)
    raise InvalidURLError("Unsupported PR URL provider")
