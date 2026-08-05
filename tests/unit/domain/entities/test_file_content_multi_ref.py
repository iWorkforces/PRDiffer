from __future__ import annotations

import pytest

from prdiffer.domain.entities import file_content


@pytest.mark.unit
def test_file_content_request_keeps_same_path_at_different_refs_distinct() -> None:
    request_type = file_content.FileContentRequest
    response_type = file_content.FileContentResponse
    head_request = request_type(repo_full_name="owner/repository", path="src/module.py", ref="head-sha")
    base_request = request_type(repo_full_name="owner/repository", path="src/module.py", ref="base-sha")

    assert head_request != base_request
    assert response_type(request=head_request, content=file_content.FileContentAvailable(text="head")).request == head_request
