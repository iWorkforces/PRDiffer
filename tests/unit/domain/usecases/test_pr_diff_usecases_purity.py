"""Tests for domain purity of pr_diff_usecases module.

Ensures the use case module does not import from infrastructure layer,
maintaining Clean Architecture boundaries.
"""

import ast
from pathlib import Path

import pytest


@pytest.mark.unit
class TestPRDiffUseCasesDomainPurity:
    """Verify pr_diff_usecases.py has no infrastructure imports."""

    def test_use_case_does_not_import_infrastructure(self):
        """Domain use case must not import from prdiffer.infrastructure."""
        source = Path("prdiffer/domain/usecases/pr_diff_usecases.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("prdiffer.infrastructure"), f"Domain violation: imports {node.module}"

    def test_use_case_does_not_import_application(self):
        """Domain use case must not import from prdiffer.application."""
        source = Path("prdiffer/domain/usecases/pr_diff_usecases.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("prdiffer.application"), f"Domain violation: imports {node.module}"
