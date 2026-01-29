"""Unit tests for rate limit handling in UnifiedRetryHandler."""

from unittest.mock import patch

import pytest

from prdiffer.infrastructure.utils.retry_handler import UnifiedRetryHandler


class FakeGithubException(Exception):
    """Minimal exception type that exposes headers/data like PyGithub."""

    def __init__(self, message, headers=None, data=None):
        super().__init__(message)
        self.headers = headers or {}
        self.data = data


@pytest.mark.unit
def test_retry_after_header_honored():
    handler = UnifiedRetryHandler(max_retries=2, retry_delay=1.0)
    sleep_calls = []
    call_count = {"count": 0}

    def flaky():
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise FakeGithubException(
                "Rate limit exceeded",
                headers={"Retry-After": "5"},
            )
        return "ok"

    with patch(
        "prdiffer.infrastructure.utils.retry_handler.time.sleep",
        lambda delay: sleep_calls.append(delay),
    ):
        result = handler.execute_with_retry(flaky)

    assert result == "ok"
    assert sleep_calls == [5.0]


@pytest.mark.unit
def test_rate_limit_reset_header_honored():
    handler = UnifiedRetryHandler(
        max_retries=2,
        retry_delay=1.0,
        rate_limit_reset_buffer=2.0,
    )
    sleep_calls = []
    call_count = {"count": 0}

    def flaky():
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise FakeGithubException(
                "Rate limit exceeded",
                headers={"X-RateLimit-Reset": "1120"},
            )
        return "ok"

    with patch(
        "prdiffer.infrastructure.utils.retry_handler.time.time",
        return_value=1000.0,
    ):
        with patch(
            "prdiffer.infrastructure.utils.retry_handler.time.sleep",
            lambda delay: sleep_calls.append(delay),
        ):
            result = handler.execute_with_retry(flaky)

    assert result == "ok"
    assert sleep_calls == [122.0]


@pytest.mark.unit
def test_secondary_rate_limit_backoff_used():
    handler = UnifiedRetryHandler(
        max_retries=2,
        retry_delay=1.0,
        secondary_rate_limit_backoff=60.0,
    )
    sleep_calls = []

    def always_fails():
        raise FakeGithubException("Abuse detection mechanism triggered")

    with patch(
        "prdiffer.infrastructure.utils.retry_handler.random.uniform",
        return_value=0.0,
    ):
        with patch(
            "prdiffer.infrastructure.utils.retry_handler.time.sleep",
            lambda delay: sleep_calls.append(delay),
        ):
            with pytest.raises(FakeGithubException):
                handler.execute_with_retry(always_fails)

    assert sleep_calls == [60.0]


@pytest.mark.unit
def test_missing_headers_fallback_to_backoff():
    handler = UnifiedRetryHandler(max_retries=2, retry_delay=1.0)
    sleep_calls = []
    call_count = {"count": 0}

    def flaky():
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise FakeGithubException("Rate limit exceeded")
        return "ok"

    with patch(
        "prdiffer.infrastructure.utils.retry_handler.random.uniform",
        return_value=0.0,
    ):
        with patch(
            "prdiffer.infrastructure.utils.retry_handler.time.sleep",
            lambda delay: sleep_calls.append(delay),
        ):
            result = handler.execute_with_retry(flaky)

    assert result == "ok"
    assert sleep_calls == [1.0]
