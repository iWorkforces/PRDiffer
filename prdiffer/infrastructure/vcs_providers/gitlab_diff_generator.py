"""Assemble ordered GitLab full-context FileDiffResponse values."""

from __future__ import annotations

from prdiffer.domain.config.gitlab_config import GitLabConfig
from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE, FilePatchInfo
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason
from prdiffer.infrastructure.github.diff_generator import DiffGenerator
from prdiffer.infrastructure.vcs_providers.gitlab_content import GitLabFileContents
from prdiffer.infrastructure.vcs_providers.gitlab_inventory import GitLabInventoryFile


class GitLabDiffAssembler:
    """Convert inventory + typed contents into ordered full-context PRDiff."""

    def __init__(
        self,
        diff_generator: DiffGenerator,
        config: GitLabConfig,
    ) -> None:
        self._diff_generator = diff_generator
        self._config = config

    def assemble(
        self,
        inventory: tuple[GitLabInventoryFile, ...],
        contents: tuple[GitLabFileContents, ...],
    ) -> PRDiff:
        if len(inventory) != len(contents):
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.DIFF_GENERATION_FAILED,
                message="Inventory/content length mismatch",
                observed=len(contents),
                limit=len(inventory),
            )

        patches: list[FilePatchInfo] = []
        for item, content in zip(inventory, contents, strict=True):
            if content.index != item.index:
                raise FullDiffIncompleteError(
                    FullDiffIncompleteReason.DIFF_GENERATION_FAILED,
                    message="Content index mismatch",
                    path=content.path,
                    observed=content.index,
                    limit=item.index,
                )
            path = content.path
            old_filename = content.previous_path if content.edit_type is EDIT_TYPE.RENAMED else None
            patches.append(
                FilePatchInfo(
                    filename=path,
                    base_file=content.base.text,
                    head_file=content.head.text,
                    patch="",  # never pass provider hunk text as output
                    edit_type=content.edit_type,
                    old_filename=old_filename,
                    old_mode=content.old_mode,
                    new_mode=content.new_mode,
                )
            )

        generated = self._diff_generator.generate_ordered_file_diffs(patches)
        if len(generated) != len(inventory):
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.DIFF_GENERATION_FAILED,
                message="Generated diff count mismatch",
                observed=len(generated),
                limit=len(inventory),
            )

        responses: list[FileDiffResponse] = []
        total_chars = 0
        for item, content, gen in zip(inventory, contents, generated, strict=True):
            if gen.index != item.index or gen.path != content.path:
                raise FullDiffIncompleteError(
                    FullDiffIncompleteReason.DIFF_GENERATION_FAILED,
                    message="Generated path/index mismatch",
                    path=gen.path,
                )

            # Equal-content equal-mode modified with no rename/mode headers is indeterminate.
            if (
                content.edit_type is EDIT_TYPE.MODIFIED
                and content.base.text == content.head.text
                and (content.old_mode is None or content.old_mode == content.new_mode)
                and not (gen.diff or "").strip()
            ):
                raise FullDiffIncompleteError(
                    FullDiffIncompleteReason.DIFF_GENERATION_FAILED,
                    message="No-op modified record produced empty full-context diff",
                    path=content.path,
                )

            # Empty textual diff only allowed for authoritative zero-byte add/delete.
            if not (gen.diff or "").strip():
                if content.edit_type is EDIT_TYPE.ADDED and content.head.text == "":
                    pass
                elif content.edit_type is EDIT_TYPE.DELETED and content.base.text == "":
                    pass
                elif content.edit_type is EDIT_TYPE.RENAMED:
                    # rename-only must still have headers
                    if "rename from" not in (gen.diff or ""):
                        raise FullDiffIncompleteError(
                            FullDiffIncompleteReason.DIFF_GENERATION_FAILED,
                            message="Rename-only missing headers",
                            path=content.path,
                        )
                else:
                    raise FullDiffIncompleteError(
                        FullDiffIncompleteReason.DIFF_GENERATION_FAILED,
                        message="Empty full-context diff is not allowed for this status",
                        path=content.path,
                    )

            additions, deletions = _count_unified_stats(gen.diff)
            previous_path = gen.previous_path if content.edit_type is EDIT_TYPE.RENAMED else None
            responses.append(
                FileDiffResponse(
                    path=content.path,
                    status=content.edit_type,
                    stats=FileStats(additions=additions, deletions=deletions),
                    diff=gen.diff,
                    previous_path=previous_path,
                )
            )
            total_chars += len(gen.diff)

        if total_chars > self._config.max_total_chars:
            raise FullDiffIncompleteError(
                FullDiffIncompleteReason.RESPONSE_SIZE_LIMIT,
                message=f"Aggregate diff size {total_chars} exceeds max_total_chars",
                observed=total_chars,
                limit=self._config.max_total_chars,
            )

        return PRDiff(files=tuple(responses))


def _count_unified_stats(diff: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return additions, deletions
