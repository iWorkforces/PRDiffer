from dataclasses import dataclass
from pathlib import Path
import subprocess

import pytest


@dataclass(frozen=True, slots=True)
class TokenScenario:
    github_token: str
    gitlab_token: str
    expects_launch: bool


@pytest.mark.integration
@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(TokenScenario("github-placeholder", "", True), id="github-only"),
        pytest.param(TokenScenario("", "gitlab-placeholder", True), id="gitlab-only"),
        pytest.param(TokenScenario("github-placeholder", "gitlab-placeholder", True), id="both"),
        pytest.param(TokenScenario("", "", False), id="neither"),
    ],
)
def test_launcher_reaches_fake_server_when_provider_tokens_vary(tmp_path: Path, scenario: TokenScenario) -> None:
    # Given
    (tmp_path / "prdiffer").mkdir()
    (tmp_path / "prdiffer" / "server.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uv = fake_bin / "uv"
    fake_uv.write_text(
        """#!/bin/bash
set -euo pipefail

case "$1" in
    --version)
        ;;
    sync)
        : > "$SYNC_MARKER"
        ;;
    run)
        if [[ "$2" == "python" && "$3" == "--version" ]]; then
            exit 0
        fi
        if [[ "$2" == "python" && "$3" == "prdiffer/server.py" ]]; then
            : > "$LAUNCH_MARKER"
            /bin/sleep 2
            exit 0
        fi
        exit 2
        ;;
    *)
        exit 2
        ;;
esac
""",
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)

    sync_marker = tmp_path / "sync-marker"
    launch_marker = tmp_path / "launch-marker"
    environment = {
        "GITHUB_TOKEN": scenario.github_token,
        "GITLAB_TOKEN": scenario.gitlab_token,
        "HOME": str(tmp_path),
        "LAUNCH_MARKER": str(launch_marker),
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "PID_FILE": str(tmp_path / "prdiffer-server.pid"),
        "SYNC_MARKER": str(sync_marker),
        "TRANSPORT": "stdio",
    }

    # When
    completed = subprocess.run(
        [
            "/bin/bash",
            str(Path(__file__).resolve().parents[2] / "start-prdiffer-mcp-server.sh"),
        ],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=environment,
        text=True,
        timeout=5,
    )

    # Then
    assert sync_marker.is_file()
    if scenario.expects_launch:
        assert completed.returncode == 0
        assert launch_marker.is_file()
    else:
        assert completed.returncode == 1
        assert not launch_marker.exists()
