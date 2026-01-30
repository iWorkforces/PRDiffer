#!/usr/bin/env python3
"""Modernize Python type hints to Python 3.14+ built-ins."""

import re
import sys
from pathlib import Path


def modernize_types(content: str) -> str:
    """Modernize type hints in Python file content."""

    # Replace imports
    content = re.sub(
        r"from typing import ([^(n)]+?)\b.*List\b", r"from typing import \1", content
    )

    # Replace list[T] → list[T]
    content = re.sub(r"\bList\[([^\]]+)\]", r"list[\1]", content)

    # Replace List → list in docstrings/comments (optional, can skip)
    # content = re.sub(r'\bList\b', r'list', content)

    # Replace dict[K, V] → dict[K, V]
    content = re.sub(r"\bDict\[([^,]+),\s*([^\]]+)\]", r"dict[\1, \2]", content)

    # Replace dict[K, V] → dict[K, V] (single key)
    content = re.sub(
        r"\bDict\[([^,]+),\s*\*\s*\*\s*\*\s*([^\]]+)\]", r"dict[\1, \2]", content
    )

    # Replace dict[T] → dict[T] (edge case)
    content = re.sub(r"\bDict\[([^\]]+)\]", r"dict[\1]", content)

    # Replace tuple[X, Y] → tuple[X, Y]
    content = re.sub(r"\bTuple\[([^,]+),\s*([^\]]+)\]", r"tuple[\1, \2]", content)

    # Replace tuple[T] → tuple[T] (edge case)
    content = re.sub(r"\bTuple\[([^\]]+)\]", r"tuple[\1]", content)

    # Replace set[T] → set[T]
    content = re.sub(r"\bSet\[([^\]]+)\]", r"set[\1]", content)

    # Replace frozenset[T] → frozenset[T]
    content = re.sub(r"\bFrozenSet\[([^\]]+)\]", r"frozenset[\1]", content)

    return content


def process_file(filepath: Path) -> bool:
    """Process a single file and return True if changes were made."""

    try:
        with open(filepath, "r") as f:
            original = f.read()

        modernized = modernize_types(original)

        if modernized == original:
            return False

        with open(filepath, "w") as f:
            f.write(modernized)

        return True

    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    files = [
        Path("prdiffer/application/components/rate_limiter.py"),
        Path("prdiffer/application/components/authentication.py"),
        Path("prdiffer/application/components/server_configuration.py"),
        Path("prdiffer/application/plugin_manager.py"),
        Path("prdiffer/infrastructure/utils/api_health_tracker.py"),
        Path("prdiffer/infrastructure/utils/pattern_matcher.py"),
        Path("prdiffer/infrastructure/utils/circuit_breaker.py"),
        Path("prdiffer/infrastructure/utils/diff_utils.py"),
        Path("prdiffer/infrastructure/github/file_processor.py"),
        Path("prdiffer/infrastructure/github/api_client.py"),
        Path("prdiffer/infrastructure/github/diff_generator.py"),
        Path("prdiffer/infrastructure/settings.py"),
        Path("prdiffer/domain/vcs_provider_registry.py"),
        Path("prdiffer/domain/services/pattern_matching.py"),
        Path("prdiffer/domain/services/github_api.py"),
        Path("prdiffer/domain/entities/file_patch.py"),
        Path("prdiffer/domain/entities/pr_diff.py"),
    ]

    changed = sum(process_file(f) for f in files)
    print(f"Modernized {changed} / {len(files)} files")
