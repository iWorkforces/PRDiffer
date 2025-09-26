from pydantic import BaseModel
from typing import Optional


class PRDiff(BaseModel):
    commit_messages: Optional[str] = None
    diff_content: str
