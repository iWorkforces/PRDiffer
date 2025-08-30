from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class EDIT_TYPE(StrEnum):
    ADDED = "added"
    DELETED = "deleted"
    MODIFIED = "modified"
    RENAMED = "renamed"
    UNKNOWN = "unknown"


@dataclass
class FilePatchInfo:
    base_file: str
    head_file: str
    patch: str
    filename: str
    tokens: int = -1
    edit_type: EDIT_TYPE = EDIT_TYPE.UNKNOWN
    old_filename: Optional[str] = None
    num_plus_lines: int = -1
    num_minus_lines: int = -1
    language: Optional[str] = None
    ai_file_summary: Optional[str] = None
