"""Helpers for enforcing diff size limits."""

from typing import Dict, Tuple


def apply_diff_limits(
    diff_content: str,
    max_chars: int,
    truncation_notice: str,
) -> tuple[str, dict[str, int | bool]]:
    """Apply size limits to diff content.

    Args:
        diff_content: Full diff content string.
        max_chars: Maximum allowed characters before truncation.
        truncation_notice: Notice appended when truncation occurs.

    Returns:
        Tuple of (diff_content, metadata) where metadata includes truncation info.
    """
    metadata: dict[str, int | bool] = {}

    if max_chars <= 0 or len(diff_content) <= max_chars:
        return diff_content, metadata

    metadata["diff_truncated"] = True
    metadata["diff_original_length"] = len(diff_content)

    truncated = diff_content[:max_chars]
    if truncation_notice:
        truncated = f"{truncated}\n{truncation_notice}"

    metadata["diff_truncated_length"] = len(truncated)
    return truncated, metadata
