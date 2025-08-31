from pydantic import BaseModel
from typing import Optional

class ExtraPRDiff(BaseModel):
    commit_messages: Optional[str] = None
    diff_content: str
