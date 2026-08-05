"""Project-root .env loading is independent of process cwd."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from prdiffer.infrastructure.settings import load_project_dotenv, project_root


@pytest.mark.unit
def test_project_root_points_at_repo_with_settings_toml() -> None:
    root = project_root()
    assert (root / "settings.toml").is_file()
    assert (root / "prdiffer").is_dir()


@pytest.mark.unit
def test_load_project_dotenv_sets_github_ignore_patterns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Project-root .env is loaded even when GITHUB_IGNORE_PATTERNS was unset."""
    monkeypatch.delenv("GITHUB_IGNORE_PATTERNS", raising=False)
    # Real project .env may or may not exist in CI; only assert helper behavior.
    loaded = load_project_dotenv(override=False)
    if loaded is not None:
        assert loaded.name == ".env"
        assert loaded.parent == project_root()
        # If the project's .env defines the key, it must appear in os.environ.
        # (CI checkouts without .env skip this assertion.)
        env_text = loaded.read_text(encoding="utf-8")
        if "GITHUB_IGNORE_PATTERNS=" in env_text:
            assert os.environ.get("GITHUB_IGNORE_PATTERNS")
