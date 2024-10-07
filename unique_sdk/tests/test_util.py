from unittest.mock import patch

import pytest

from unique_sdk._util import APIError, retry_on_error


# ---- Synchronous Function Tests ----
def test_retry_on_error_sync_success():
    """Test decorator on a sync function with no retries (success on first attempt)."""

    @retry_on_error(max_retries=3)
    def func():
        return "Success"

    result = func()
    assert result == "Success"


@patch("time.sleep", return_value=None)
def test_retry_on_error_sync_retries_on_specific_error(mock_sleep):
    """Test sync function retries when specific error message is encountered."""

    @retry_on_error(max_retries=3, error_messages=["Retry this error"])
    def func():
        raise ConnectionError("Retry this error")

    with pytest.raises(APIError, match="Failed after 3 attempts"):
        func()
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

    @retry_on_error(max_retries=3)
    async def func():
        return "Success"

    result = await func()
    assert result == "Success"


@pytest.mark.asyncio
@patch("asyncio.sleep", return_value=None)
async def test_retry_on_error_async_retries_on_specific_error(mock_async_sleep):
    """Test async function retries when specific error message is encountered."""

    @retry_on_error(max_retries=3, error_messages=["Retry this error"])
    async def func():
        raise ConnectionError("Retry this error")

    with pytest.raises(APIError, match="Failed after 3 attempts"):
        await func()
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
