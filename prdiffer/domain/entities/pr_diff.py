from dataclasses import dataclass, field

from prdiffer.domain.entities.file_diff_response import FileDiffResponse


@dataclass(frozen=True)
class PRDiff:
    """Domain entity representing a pull request diff content.

    This entity contains structured file-level diff information for PR analysis.
    Breaking change: files array replaces diff_content field.

    Field mapping from FilePatchInfo:
    - list[FilePatchInfo] → list[FileDiffResponse] (with mapping)
    """

    files: tuple[FileDiffResponse, ...] = field(default_factory=tuple)
