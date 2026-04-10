"""GitHub PR operation methods (approve, update description).

Extracted from github_repository.py for maintainability.
Contains PR approval and description update operations.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import asyncer
from github.GithubException import GithubException
from github.PullRequest import PullRequest

from prdiffer.infrastructure.security.input_validator import InputValidator
from prdiffer.domain.services.logger import LoggerServiceInterface
from prdiffer.infrastructure.github_repository_utils import _handle_github_exception


class GitHubPROperationsMixin:
    """Mixin providing PR approval and description update operations.

    Requires the host class to provide:
        - self._input_validator: InputValidator
        - self._repo_owner: str
        - self._repo_name: str
        - self._pr_number: int
        - self._logger: LoggerServiceInterface
        - self._pull_request: PullRequest | None
        - self._initialize_github_objects(): async method
    """

    # Type annotations for host class attributes used by this mixin
    _input_validator: InputValidator
    _logger: LoggerServiceInterface
    _repo_owner: str
    _repo_name: str
    _pr_number: int
    _initialize_github_objects: Callable[[], Coroutine[Any, Any, None]]
    _pull_request: PullRequest | None

    async def approve_pr_with_comment(self, pr_url: str, compliment: str) -> str:
        """Approve a GitHub PR with a compliment comment.

        This method:
        1. Parses the PR URL to extract owner, repo, and PR number
        2. Validates PR exists and is accessible
        3. Calls pr.create_review() with event="APPROVE" and the compliment as body
        4. Returns success message or raises exceptions loudly on failures

        Args:
            pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            compliment: The compliment text to include in the approval review

        Returns:
            str: Success message indicating PR was approved

        Raises:
            InvalidURLError: If PR URL format is invalid
            RuntimeError: If GitHub objects failed to initialize
            GithubException: If PR approval fails (404, 403, rate limit, etc.)
        """

        if not isinstance(compliment, str):
            raise ValueError("Compliment must be a string")

        if not compliment:
            raise ValueError("Compliment cannot be empty")

        safe_compliment = self._input_validator.sanitize_for_logging(compliment, max_length=500)

        repo_owner, repo_name, pr_number = self._input_validator.validate_github_url(pr_url)

        if repo_owner != self._repo_owner or repo_name != self._repo_name:
            self._logger.warning(
                f"PR URL components do not match repository instance: expected {self._repo_owner}/{self._repo_name}, got {repo_owner}/{repo_name}",
                pr_url=pr_url[:100],
            )

        if pr_number != self._pr_number:
            self._logger.warning(
                f"PR number does not match repository instance: expected {self._pr_number}, got {pr_number}",
                pr_url=pr_url[:100],
            )

        self._logger.info(
            f"Approving PR #{pr_number} in {repo_owner}/{repo_name}",
            pr_number=pr_number,
            repo=repo_name,
            owner=repo_owner,
            compliment=safe_compliment,
        )

        await self._initialize_github_objects()

        if self._pull_request is None:
            raise RuntimeError(
                f"Failed to access pull request #{pr_number} in repository {repo_owner}/{repo_name} - pull request may not exist or be inaccessible"
            )

        try:
            pull_request = self._pull_request
            review = await asyncer.asyncify(pull_request.create_review)(
                event="APPROVE",
                body=compliment,
            )

            self._logger.info(
                f"Successfully approved PR #{pr_number}",
                pr_number=pr_number,
                review_id=review.id if hasattr(review, "id") else "unknown",
            )

            return f"Successfully approved PR #{pr_number} in {repo_owner}/{repo_name}"

        except GithubException as e:
            _handle_github_exception(
                e,
                self._logger,
                pr_number=pr_number,
                repo_owner=repo_owner,
                repo_name=repo_name,
                operation="approving",
            )
            # unreachable - _handle_github_exception always raises
            raise  # pragma: no cover

    async def update_pr_description(self, pr_url: str, description: str) -> str:
        """Update a GitHub PR description/body.

        This method:
        1. Parses the PR URL to extract owner, repo, and PR number
        2. Validates PR exists and is accessible
        3. Calls pr.edit(body=description) to update the description
        4. Returns success message or raises exceptions loudly on failures

        Args:
            pr_url: The full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            description: The new description text to set on the PR

        Returns:
            str: Success message indicating PR description was updated

        Raises:
            InvalidURLError: If PR URL format is invalid
            RuntimeError: If GitHub objects failed to initialize
            GithubException: If PR update fails (404, 403, rate limit, etc.)
        """

        if not isinstance(description, str):
            raise ValueError("Description must be a string")

        if not description:
            raise ValueError("Description cannot be empty")

        safe_description = self._input_validator.sanitize_for_logging(description, max_length=500)

        repo_owner, repo_name, pr_number = self._input_validator.validate_github_url(pr_url)

        if repo_owner != self._repo_owner or repo_name != self._repo_name:
            self._logger.warning(
                f"PR URL components do not match repository instance: expected {self._repo_owner}/{self._repo_name}, got {repo_owner}/{repo_name}",
                pr_url=pr_url[:100],
            )

        if pr_number != self._pr_number:
            self._logger.warning(
                f"PR number does not match repository instance: expected {self._pr_number}, got {pr_number}",
                pr_url=pr_url[:100],
            )

        self._logger.info(
            f"Updating description for PR #{pr_number} in {repo_owner}/{repo_name}",
            pr_number=pr_number,
            repo=repo_name,
            owner=repo_owner,
            description_preview=safe_description,
        )

        await self._initialize_github_objects()

        if self._pull_request is None:
            raise RuntimeError(
                f"Failed to access pull request #{pr_number} in repository {repo_owner}/{repo_name} - pull request may not exist or be inaccessible"
            )

        try:
            pull_request = self._pull_request
            await asyncer.asyncify(pull_request.edit)(body=description)

            self._logger.info(
                f"Successfully updated description for PR #{pr_number}",
                pr_number=pr_number,
            )

            return f"Successfully updated description for PR #{pr_number} in {repo_owner}/{repo_name}"

        except GithubException as e:
            _handle_github_exception(
                e,
                self._logger,
                pr_number=pr_number,
                repo_owner=repo_owner,
                repo_name=repo_name,
                operation="updating description for",
            )
            # unreachable - _handle_github_exception always raises
            raise  # pragma: no cover
