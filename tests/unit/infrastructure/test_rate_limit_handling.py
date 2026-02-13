"""Unit tests for rate limit handling in UnifiedRetryHandler."""

import time as time_module
from unittest.mock import patch

import pytest
from github import GithubException

from prdiffer.infrastructure.utils.retry import UnifiedRetryHandler


class FakeGithubException(GithubException):
    """Minimal exception type that exposes headers/data like PyGithub.

    Inherits from GithubException to be included in RETRY_EXCEPTIONS.
    """

    def __init__(self, message, headers=None, data=None):
        super().__init__(403, data, headers or {}, message)


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
        "prdiffer.infrastructure.utils.retry.handler.time.sleep",
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

    # Patch time.time directly since it's imported locally in delay_calculator
    with patch.object(time_module, "time", return_value=1000.0):
        with patch(
            "prdiffer.infrastructure.utils.retry.handler.time.sleep",
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

    # Patch random.uniform in delay_calculator where it's actually imported
    with patch(
        "prdiffer.infrastructure.utils.delay_calculator.random.uniform",
        return_value=0.0,
    ):
        with patch(
            "prdiffer.infrastructure.utils.retry.handler.time.sleep",
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

    # Patch random.uniform in delay_calculator where it's actually imported
    with patch(
        "prdiffer.infrastructure.utils.delay_calculator.random.uniform",
        return_value=0.0,
    ):
        with patch(
            "prdiffer.infrastructure.utils.retry.handler.time.sleep",
            lambda delay: sleep_calls.append(delay),
        ):
            result = handler.execute_with_retry(flaky)

    assert result == "ok"
    # Rate limit errors get double delay: base_delay * 2 = 1.0 * 2 = 2.0
    assert sleep_calls == [2.0]
