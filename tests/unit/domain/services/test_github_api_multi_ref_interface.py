from __future__ import annotations

import pytest

from prdiffer.domain.services.github_api import GitHubAPIServiceInterface


@pytest.mark.unit
def test_github_api_interface_requires_multi_ref_content_batch() -> None:
    assert "get_files_content_multi_ref_batch" in GitHubAPIServiceInterface.__abstractmethods__
