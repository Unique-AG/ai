from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk import ContextMemory as PublicContextMemory
from unique_sdk.api_resources._context_memory import ContextMemory

pytestmark = pytest.mark.ai

USER_ID = "user_1"
COMPANY_ID = "company_1"
MEMORY = {
    "scopeId": "scope_1",
    "contentId": "content_1",
    "document": "Remember this",
    "updatedAt": "2026-09-16T12:00:00.000Z",
    "object": "context-memory",
}


def test_context_memory_is_exported():
    assert PublicContextMemory is ContextMemory


@patch.object(ContextMemory, "_static_request")
def test_retrieve_requests_context_memory(mock_request):
    mock_request.return_value = MEMORY

    result = ContextMemory.retrieve(USER_ID, COMPANY_ID)

    mock_request.assert_called_once_with(
        "get",
        "/context-memory",
        USER_ID,
        COMPANY_ID,
    )
    assert result == MEMORY


@patch.object(ContextMemory, "_static_request")
def test_modify_patches_document(mock_request):
    mock_request.return_value = MEMORY

    result = ContextMemory.modify(
        USER_ID,
        COMPANY_ID,
        document="Remember this",
    )

    mock_request.assert_called_once_with(
        "patch",
        "/context-memory",
        USER_ID,
        COMPANY_ID,
        params={"document": "Remember this"},
    )
    assert result == MEMORY


@patch.object(ContextMemory, "_static_request_async", new_callable=AsyncMock)
async def test_retrieve_async_requests_context_memory(mock_request):
    mock_request.return_value = MEMORY

    result = await ContextMemory.retrieve_async(USER_ID, COMPANY_ID)

    mock_request.assert_awaited_once_with(
        "get",
        "/context-memory",
        USER_ID,
        COMPANY_ID,
    )
    assert result == MEMORY


@patch.object(ContextMemory, "_static_request_async", new_callable=AsyncMock)
async def test_modify_async_patches_document(mock_request):
    mock_request.return_value = MEMORY

    result = await ContextMemory.modify_async(
        USER_ID,
        COMPANY_ID,
        document="Remember this",
    )

    mock_request.assert_awaited_once_with(
        "patch",
        "/context-memory",
        USER_ID,
        COMPANY_ID,
        params={"document": "Remember this"},
    )
    assert result == MEMORY
