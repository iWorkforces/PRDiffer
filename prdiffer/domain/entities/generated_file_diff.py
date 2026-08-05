"""Identity-bearing full-context diff generation results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedFileDiff:
    """One generated public full-context diff for a selected file.

    ``index`` is the provider/selection order. ``previous_path`` is set for renames.
    ``diff`` is the generated full-context string (not the provider hunk alone).
    """

    index: int
    path: str
    previous_path: str | None
    diff: str
