from pathlib import Path
import tomllib

from prdiffer.version import __version__


def test_version_matches_pyproject():
    data = tomllib.loads(Path('pyproject.toml').read_text())
    assert data['project']['version'] == __version__
