"""In-process FastMCP surface tests for strict full-diff responses."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

from prdiffer.application.tool_registry import ToolRegistry
from prdiffer.domain.entities.file_diff_response import FileDiffResponse, FileStats
from prdiffer.domain.entities.file_patch import EDIT_TYPE
from prdiffer.domain.entities.pr_diff import PRDiff
from prdiffer.domain.exceptions import FullDiffIncompleteError, FullDiffIncompleteReason


def _mixed_pr_diff() -> PRDiff:
    return PRDiff(
        files=(
            FileDiffResponse(
                path="mod.py",
                status=EDIT_TYPE.MODIFIED,
                stats=FileStats(additions=1, deletions=1),
                diff="@@ full\n context\n-old\n+new\n",
            ),
            FileDiffResponse(
                path="gone.py",
                status=EDIT_TYPE.DELETED,
                stats=FileStats(additions=0, deletions=1),
                diff="@@\n-line\n",
            ),
            FileDiffResponse(
                path="new_name.py",
                status=EDIT_TYPE.RENAMED,
                stats=FileStats(additions=0, deletions=0),
                diff="rename from old_name.py\nrename to new_name.py\n",
                previous_path="old_name.py",
            ),
        )
    )


def _registry(pr_diff: PRDiff | None = None, *, fail: Exception | None = None) -> ToolRegistry:
    logger = MagicMock()
    rate = MagicMock()
    rate.check_rate_limit.return_value = True
    rate.get_rate_limit_info.return_value = {"max_requests": 100, "window_seconds": 60}
    metrics = MagicMock()
    metrics.generate_request_id.return_value = "req-1"
    metrics.track_request = MagicMock()
    auth = MagicMock()
    auth.authenticate.return_value = (True, "client-1")
    validator = MagicMock()
    validator.sanitize_string.side_effect = lambda s, max_length=1000: s
    validator.validate_github_url.return_value = ("owner", "repo", 1)

    registry = ToolRegistry(
        pr_diff_service=MagicMock(),
        cache_service=MagicMock(),
        logger=logger,
        github_repository_class=MagicMock(),
        rate_limiter=rate,
        metrics_tracker=metrics,
        authentication=auth,
        input_validator=validator,
        request_coalescing_service=MagicMock(),
        cache_hit_optimization_enabled=False,
    )

    async def coalesce(key, fn, timeout=None):
        if fail is not None:
            raise fail
        return pr_diff if pr_diff is not None else await fn()

    registry._request_coalescing.coalesce = AsyncMock(side_effect=coalesce)
    return registry


@pytest.mark.integration
@pytest.mark.anyio
async def test_registered_get_pr_diff_success_surface() -> None:
    """Registered tool returns ordered complete diffs with previous_path."""
    mcp = FastMCP("test-prdiffer")
    registry = _registry(_mixed_pr_diff())
    registry.register_tools(mcp)

    # Locate registered tool function
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "get_pr_diff" in names

    with patch(
        "prdiffer.application.tool_registry.parse_pr_target",
        return_value=MagicMock(provider="github", repo_owner="owner", repo_name="repo", pr_number=1),
    ):
        # Call tool through FastMCP call_tool if available
        result = await mcp.call_tool(
            "get_pr_diff",
            {"pr_url": "https://github.com/owner/repo/pull/1"},
        )

    # Prefer structured_content from FastMCP ToolResult
    if hasattr(result, "structured_content") and result.structured_content:
        payload = result.structured_content
    elif hasattr(result, "content") and result.content:
        import json

        payload = json.loads(result.content[0].text)
    else:
        payload = result

    files = payload.get("files", []) if isinstance(payload, dict) else []
    assert len(files) == 3
    rename = next(f for f in files if f["path"] == "new_name.py")
    assert rename["previous_path"] == "old_name.py"
    assert rename["status"] == "renamed"
    # Full-context style payload present for modified file
    mod = next(f for f in files if f["path"] == "mod.py")
    assert "context" in mod["diff"] or "old" in mod["diff"]


@pytest.mark.integration
@pytest.mark.anyio
async def test_registered_get_pr_diff_strict_binary_failure() -> None:
    import json

    from fastmcp.exceptions import ToolError

    mcp = FastMCP("test-prdiffer-fail")
    err = FullDiffIncompleteError(
        FullDiffIncompleteReason.BINARY_CONTENT,
        path="bin.dat",
        previous_path="old.bin",
        observed=9,
        limit=8,
    )
    registry = _registry(fail=err)
    registry.register_tools(mcp)

    with patch(
        "prdiffer.application.tool_registry.parse_pr_target",
        return_value=MagicMock(provider="github", repo_owner="owner", repo_name="repo", pr_number=1),
    ):
        with pytest.raises(ToolError) as exc_info:
            await mcp.call_tool(
                "get_pr_diff",
                {"pr_url": "https://github.com/owner/repo/pull/1"},
            )

    # FastMCP.call_tool raises ToolError; wire protocol maps this to isError=true.
    # Body is compact JSON with stable top-level keys and safe E5020 details only.
    payload = json.loads(str(exc_info.value))
    assert list(payload.keys()) == ["error_code", "message", "details"]
    assert payload["error_code"] == "E5020_FULL_DIFF_INCOMPLETE"
    assert payload["details"]["reason"] == "BINARY_CONTENT"
    assert payload["details"]["path"] == "bin.dat"
    assert payload["details"]["previous_path"] == "old.bin"
    assert payload["details"]["observed"] == 9
    assert payload["details"]["limit"] == 8
    assert "files" not in payload
    assert "files" not in json.dumps(payload)


@pytest.mark.integration
@pytest.mark.anyio
async def test_gitlab_nested_success_and_e5020_surface() -> None:
    import json
    from fastmcp.exceptions import ToolError

    mcp = FastMCP("test-gitlab-mcp")
    success = PRDiff(
        files=(
            FileDiffResponse(
                path="new.py",
                status=EDIT_TYPE.RENAMED,
                stats=FileStats(additions=0, deletions=0),
                diff="old mode 100644\nnew mode 100755\nrename from old.py\nrename to new.py\n",
                previous_path="old.py",
            ),
        )
    )
    registry = _registry(success)
    # Force GitLab routing
    registry._gitlab_reader = MagicMock()
    registry.register_tools(mcp)

    with patch(
        "prdiffer.application.tool_registry.parse_pr_target",
        return_value=MagicMock(provider="gitlab", repo_owner="group/sub", repo_name="project", pr_number=42),
    ):
        result = await mcp.call_tool(
            "get_pr_diff",
            {"pr_url": "https://gitlab.com/group/sub/project/-/merge_requests/42"},
        )
    if hasattr(result, "structured_content") and result.structured_content:
        payload = result.structured_content
    else:
        payload = json.loads(result.content[0].text)
    files = payload.get("files", [])
    assert len(files) == 1
    assert files[0]["previous_path"] == "old.py"

    # E5020 path
    mcp2 = FastMCP("test-gitlab-e5020")
    err = FullDiffIncompleteError(FullDiffIncompleteReason.BINARY_CONTENT, path="x.bin")
    reg2 = _registry(fail=err)
    reg2._gitlab_reader = MagicMock()
    reg2.register_tools(mcp2)
    with patch(
        "prdiffer.application.tool_registry.parse_pr_target",
        return_value=MagicMock(provider="gitlab", repo_owner="group/sub", repo_name="project", pr_number=42),
    ):
        with pytest.raises(ToolError) as exc:
            await mcp2.call_tool(
                "get_pr_diff",
                {"pr_url": "https://gitlab.com/group/sub/project/-/merge_requests/42"},
            )
    body = json.loads(str(exc.value))
    assert body["error_code"] == "E5020_FULL_DIFF_INCOMPLETE"
    assert "files" not in body
