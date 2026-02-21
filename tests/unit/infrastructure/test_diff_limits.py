from prdiffer.infrastructure.utils.diff_limits import apply_diff_limits


def test_apply_diff_limits_truncates_and_reports_metadata():
    content = 'a' * 50
    truncated, metadata = apply_diff_limits(content, max_chars=10, truncation_notice='[TRUNC]')

    assert metadata['diff_truncated'] is True
    assert metadata['diff_original_length'] == 50
    assert metadata['diff_truncated_length'] == len(truncated)
    assert '[TRUNC]' in truncated


def test_apply_diff_limits_noop_when_under_limit():
    content = 'short'
    truncated, metadata = apply_diff_limits(content, max_chars=100, truncation_notice='[TRUNC]')

    assert truncated == content
    assert metadata == {}
