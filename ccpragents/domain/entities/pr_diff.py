from pydantic import BaseModel, Field
from typing import Optional


class PRDiff(BaseModel):
    """Domain entity representing a pull request with diff content and commit messages.

    This entity contains only the essential diff content and commit messages
    for PR analysis, excluding all other metadata and statistics.
    """

    diff_content: str = Field("", description="Combined diff content for all files")
    commit_messages: Optional[str] = Field(
        None, description="Formatted commit messages"
    )
