#!/usr/bin/env python3
"""Modernize Python type hints to Python 3.14+ built-ins."""

import re
import sys
from pathlib import Path


def modernize_file(filepath: Path) -> bool:
    """Modernize type hints in a single Python file."""

    try:
        with open(filepath, "r") as f:
            content = f.read()

        original = content

        # Replace List[T] → list[T]
        content = re.sub(r"\bList\[([^\]]+)\]", r"list[\1]", content)

        # Replace Dict[K, V] → dict[K, V]
        content = re.sub(r"\bDict\[([^,]+),\s*([^\]]+)\]", r"dict[\1, \2]", content)

        # Replace Tuple[X, Y] → tuple[X, Y]
        content = re.sub(r"\bTuple\[([^,]+),\s*([^\]]+)\]", r"tuple[\1, \2]", content)

        # Replace Set[T] → set[T]
        content = re.sub(r"\bSet\[([^\]]+)\]", r"set[\1]", content)

        # Replace FrozenSet[T] → frozenset[T]
        content = re.sub(r"\bFrozenSet\[([^\]]+)\]", r"frozenset[\1]", content)

        # Replace Dict[T] → dict[T] (edge case)
        content = re.sub(r"\bDict\[([^\]]+)\]", r"dict[\1]", content)

        # Replace Tuple[T] → tuple[T] (edge case)
        content = re.sub(r"\bTuple\[([^\]]+)\]", r"tuple[\1]", content)

        if content == original:
            return False

        with open(filepath, "w") as f:
            f.write(content)

        return True

    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    # Find all Python files with old-style type imports
    files_to_check = []
    for py_file in Path(".").rglob("**/*.py"):
        if "tests/" in str(py_file) and ".py" in py_file.parts:
            continue  # Skip test files for now
        try:
            with open(py_file, "r") as f:
                first_lines = f.read(500)
                if "from typing import" in first_lines and (
                    "List" in first_lines
                    or "Dict" in first_lines
                    or "Tuple" in first_lines
                    or "Set" in first_lines
                ):
                    files_to_check.append(py_file)
        except Exception:
            pass

    print(f"Found {len(files_to_check)} files to modernize")
    changed = sum(modernize_file(f) for f in files_to_check)
    print(f"Modernized {changed} / {len(files_to_check)} files")
