from unittest.mock import patch

import pytest

from unique_sdk._util import APIError, retry_on_error


# ---- Synchronous Function Tests ----
def test_retry_on_error_sync_success():
    """Test decorator on a sync function with no retries (success on first attempt)."""

    @retry_on_error(max_retries=3, error_messages=[])
    def func():
        return "Success"

    result = func()
    assert result == "Success"


@patch("time.sleep", return_value=None)
def test_retry_on_error_sync_retries_on_specific_error(mock_sleep):
    """Test sync function retries when specific error message is encountered."""

    source = APIError("Retry this error")

    @retry_on_error(max_retries=3, error_messages=["Retry this error"])
    def func():
        raise source

    with pytest.raises(APIError) as caught:
        func()
    assert caught.value is source
    assert mock_sleep.call_count == 2  # Should sleep twice (between retries)


@patch("time.sleep", return_value=None)
def test_retry_on_error_sync_no_retry_on_different_error(mock_sleep):
    """Test sync function doesn't retry on different error message."""

    @retry_on_error(max_retries=3, error_messages=["Retry this error"])
    def func():
        raise ConnectionError("Different error")

    with pytest.raises(ConnectionError, match="Different error"):
        func()
    mock_sleep.assert_not_called()  # No retries, so no sleep


# ---- Asynchronous Function Tests ----
@pytest.mark.asyncio
async def test_retry_on_error_async_success():
    """Test decorator on an async function with no retries (success on first attempt)."""

    @retry_on_error(max_retries=3, error_messages=[])
    async def func():
        return "Success"

    result = await func()
    assert result == "Success"


@pytest.mark.asyncio
@patch("asyncio.sleep", return_value=None)
async def test_retry_on_error_async_retries_on_specific_error(mock_async_sleep):
    """Test async function retries when specific error message is encountered."""

    source = APIError("Retry this error")

    @retry_on_error(max_retries=3, error_messages=["Retry this error"])
    async def func():
        raise source

    with pytest.raises(APIError) as caught:
        await func()
    assert caught.value is source
    assert mock_async_sleep.call_count == 2  # Should sleep twice (between retries)


@pytest.mark.asyncio
@patch("asyncio.sleep", return_value=None)
async def test_retry_on_error_async_no_retry_on_different_error(mock_async_sleep):
    """Test async function doesn't retry on different error message."""

    @retry_on_error(max_retries=3, error_messages=["Retry this error"])
    async def func():
        raise ConnectionError("Different error")

    with pytest.raises(ConnectionError, match="Different error"):
        await func()
    mock_async_sleep.assert_not_called()  # No retries, so no sleep


@pytest.mark.ai
@patch("time.sleep", return_value=None)
def test_retry_on_error__does_not_retry__http_4xx(mock_sleep) -> None:
    """Purpose: Verify a 4xx API error is returned on the first attempt.
    Why this matters: Content-filter and other client errors must not be retried.
    Setup summary: Raise a 400 whose message matches a retry string.
    """
    source = APIError(
        "You can retry your request",
        http_status=400,
        code="content_filter",
        params={"retryable": False},
    )

    @retry_on_error(max_retries=3, error_messages=["retry your request"])
    def func():
        raise source

    with pytest.raises(APIError) as caught:
        func()

    assert caught.value is source
    mock_sleep.assert_not_called()


@pytest.mark.ai
@patch("time.sleep", return_value=None)
def test_retry_on_error__does_not_log__when_not_retried(mock_sleep, caplog) -> None:
    """Purpose: Verify an error that is not retried writes no retry log.
    Why this matters: A "Retrying" line before an immediate raise is misleading.
    Setup summary: Raise a content-filter 400 and capture the unique logger.
    """

    @retry_on_error(max_retries=3, error_messages=[])
    def func():
        raise APIError("filtered", http_status=400, code="content_filter")

    with caplog.at_level("DEBUG", logger="unique"), pytest.raises(APIError):
        func()

    assert caplog.records == []


@pytest.mark.ai
@patch("time.sleep", return_value=None)
def test_retry_on_error__logs_retry_fields_without_message(mock_sleep, caplog) -> None:
    """Purpose: Verify a retry logs code, status and correlation id, not the message.
    Why this matters: The message can carry upstream provider text.
    Setup summary: Raise a retryable 503 with a legacy original error twice.
    """
    source = APIError(
        "upstream failed",
        http_status=503,
        code="provider_unavailable",
        original_error="provider_error: secret upstream text",
        params={"retryable": True, "correlationId": "req_1"},
    )

    @retry_on_error(max_retries=3, error_messages=[], should_retry_5xx=True)
    def func():
        raise source

    with caplog.at_level("DEBUG", logger="unique"), pytest.raises(APIError):
        func()

    assert [record.getMessage() for record in caplog.records] == [
        "Retrying Unique API call, attempt 2 of 3: "
        "code=provider_unavailable http_status=503 correlation_id=req_1",
        "Retrying Unique API call, attempt 3 of 3: "
        "code=provider_unavailable http_status=503 correlation_id=req_1",
    ]
    assert all(record.levelname == "WARNING" for record in caplog.records)


@pytest.mark.ai
@patch("time.sleep", return_value=None)
def test_retry_on_error__does_not_retry__5xx_marked_not_retryable(mock_sleep) -> None:
    """Purpose: Verify a 5xx with params.retryable false is returned on the first attempt.
    Why this matters: node-chat marks unknown and provider_auth_failed as not retryable.
    Setup summary: Raise a 500 with retryable false while 5xx retries are enabled.
    """
    source = APIError(
        "Something went wrong",
        http_status=500,
        code="unknown",
        params={"retryable": False},
    )

    @retry_on_error(max_retries=3, error_messages=[], should_retry_5xx=True)
    def func():
        raise source

    with pytest.raises(APIError) as caught:
        func()

    assert caught.value is source
    mock_sleep.assert_not_called()
