"""Tests for async-corrected SDK methods that previously called sync _static_request."""

from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.api_resources._agentic_table import AgenticTable


@pytest.mark.asyncio
async def test_set_column_metadata_uses_async_request():
    with patch.object(
        AgenticTable, "_static_request_async", new_callable=AsyncMock
    ) as mock_req:
        mock_req.return_value = {"status": True, "message": None}

        result = await AgenticTable.set_column_metadata(
            user_id="u1",
            company_id="c1",
            tableId="t1",
            columnOrder=0,
        )

        mock_req.assert_awaited_once()
        assert result["status"] is True


@pytest.mark.asyncio
async def test_wait_for_ingestion_completion_uses_async_search():
    with patch(
        "unique_sdk.utils.file_io.Content.search_async", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = [{"ingestionState": "FINISHED"}]

        from unique_sdk.utils.file_io import wait_for_ingestion_completion

        state = await wait_for_ingestion_completion(
            user_id="u1",
            company_id="c1",
            content_id="cnt1",
            chat_id="ch1",
            poll_interval=0.01,
            max_wait=0.1,
        )

        mock_search.assert_awaited()
        assert state == "FINISHED"
