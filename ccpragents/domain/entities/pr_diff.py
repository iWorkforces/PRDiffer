from pydantic import BaseModel
from typing import Optional


class PRDiff(BaseModel):
    pr_number: int
    repo_owner: str
    repo_name: str
    diff_content: str
    base_commit: Optional[str] = None
    head_commit: Optional[str] = None
    changed_files: int = 0
    additions: int = 0
    deletions: int = 0


class ExtraPRDiff(PRDiff):
    commit_messages: Optional[str] = None
    reviewers: Optional[list[str]] = None
    labels: Optional[list[str]] = None
    milestone: Optional[str] = None
