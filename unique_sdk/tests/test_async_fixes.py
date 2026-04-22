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
async def test_get_sheet_data_forwards_include_sheet_metadata_query_param():
    with patch.object(
        AgenticTable, "_static_request_async", new_callable=AsyncMock
    ) as mock_req:
        mock_req.return_value = {
            "sheetId": "s1",
            "name": "n",
            "state": "IDLE",
            "chatId": "ch1",
            "createdBy": "u0",
            "companyId": "c1",
            "createdAt": "t0",
            "magicTableRowCount": 0,
        }

        await AgenticTable.get_sheet_data(
            user_id="u1",
            company_id="c1",
            tableId="t1",
            includeCells=True,
            includeSheetMetadata=True,
        )

        mock_req.assert_awaited_once()
        _method, _url, _uid, _cid, params = mock_req.await_args[0]
        assert params["tableId"] == "t1"
        assert params["includeCells"] is True
        assert params["includeSheetMetadata"] is True


@pytest.mark.asyncio
async def test_get_sheet_data_forwards_include_row_metadata_query_param():
    with patch.object(
        AgenticTable, "_static_request_async", new_callable=AsyncMock
    ) as mock_req:
        mock_req.return_value = {
            "sheetId": "s1",
            "name": "n",
            "state": "IDLE",
            "chatId": "ch1",
            "createdBy": "u0",
            "companyId": "c1",
            "createdAt": "t0",
            "magicTableRowCount": 0,
        }

        await AgenticTable.get_sheet_data(
            user_id="u1",
            company_id="c1",
            tableId="t1",
            includeCells=True,
            includeRowMetadata=True,
        )

        mock_req.assert_awaited_once()
        _method, _url, _uid, _cid, params = mock_req.await_args[0]
        assert params["tableId"] == "t1"
        assert params["includeCells"] is True
        assert params["includeRowMetadata"] is True


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
