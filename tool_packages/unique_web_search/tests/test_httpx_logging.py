import asyncio
import logging

import pytest

from unique_web_search.services.httpx_logging import hide_httpx_request_logs


@pytest.mark.ai
async def test_hide_httpx_request_logs__drops_request_lines__only_inside_scope(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Purpose: Verify httpx request lines are dropped inside the scope, including from tasks it starts.
    Why this matters: The lines carry full request URLs, but httpx logs elsewhere in the process must stay.
    Setup summary: Log request lines inside the scope, from a gathered task, and after the scope ends.
    """
    httpx_logger = logging.getLogger("httpx")

    async def log_request(label: str) -> None:
        httpx_logger.info("HTTP Request: GET https://example.com/?q=%s", label)

    with caplog.at_level(logging.INFO, logger="httpx"):
        with hide_httpx_request_logs():
            await log_request("hidden")
            await asyncio.gather(log_request("hidden-task"))
        await log_request("kept")

    assert "hidden" not in caplog.text
    assert "q=kept" in caplog.text
