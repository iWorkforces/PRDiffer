from typing import List

from pydantic import BaseModel, Field

from prdiffer.domain.entities.file_diff_response import FileDiffResponse


class PRDiff(BaseModel):
    """Domain entity representing a pull request diff content.

    This entity contains structured file-level diff information for PR analysis.
    Breaking change: files array replaces diff_content field.

    Field mapping from FilePatchInfo:
    - List[FilePatchInfo] → List[FileDiffResponse] (with mapping)
    """

    files: List[FileDiffResponse] = Field(
        default_factory=list, description="Array of file-level diff responses"
    )
