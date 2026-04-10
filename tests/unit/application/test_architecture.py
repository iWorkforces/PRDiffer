"""Architecture boundary tests — verify application layer doesn't import infrastructure directly."""

import ast
from pathlib import Path

import pytest

APPLICATION_DIR = Path("prdiffer/application")
COMPOSITION_ROOT = "factory.py"  # Only file allowed to import infrastructure


def get_top_level_imports(filepath: Path) -> list[str]:
    """Get only top-level (module-scope) imports, ignoring lazy imports inside functions/methods."""
    source = filepath.read_text()
    tree = ast.parse(source)
    modules = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.ClassDef):
            # Check class-level imports (still top-level architectural deps)
            for class_node in ast.iter_child_nodes(node):
                if isinstance(class_node, ast.ImportFrom) and class_node.module:
                    modules.append(class_node.module)
    return modules


@pytest.mark.unit
def test_no_application_imports_infrastructure():
    """Application layer must not directly import infrastructure (use domain protocols instead)."""
    violations = []
    for py_file in APPLICATION_DIR.rglob("*.py"):
        if py_file.name == COMPOSITION_ROOT:
            continue  # Composition root exception
        if py_file.name == "__init__.py":
            continue
        for module in get_top_level_imports(py_file):
            if module.startswith("prdiffer.infrastructure"):
                violations.append(f"{py_file}: imports {module}")
    assert violations == [], "Architecture violations found:\n" + "\n".join(violations)
