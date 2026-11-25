"""InternalSearchTool must only honour the tool arguments it declares (UN-28688).

These tests run the real tool, ``ContentService`` and ``ChatEvent``; only the
``unique_sdk`` HTTP calls (search and message-step logs) are replaced.
"""

import asyncio
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import unique_sdk
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)
from unique_toolkit.language_model.schemas import LanguageModelFunction

from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.service import InternalSearchTool

SPACE_FILTER: dict[str, Any] = {
    "path": ["folderIdPath"],
    "operator": "contains",
    "value": "scope_space",
}
OTHER_FOLDER_FILTER: dict[str, Any] = {
    "path": ["folderIdPath"],
    "operator": "contains",
    "value": "scope_outside_space",
}
MESSAGE_LOG: dict[str, Any] = {
    "id": "log_1",
    "messageId": "assistant_message_1",
    "status": "RUNNING",
    "text": "",
    "order": 1,
    "details": {},
    "uncitedReferences": {"data": []},
    "references": [],
    "createdAt": None,
    "updatedAt": None,
}


def _chat_event(metadata_filter: dict[str, Any] | None) -> ChatEvent:
    return ChatEvent(
        id="event_1",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        user_id="user_1",
        company_id="company_1",
        payload=ChatEventPayload(
            name="UniqueAi",
            description="",
            configuration={},
            chat_id="chat_1",
            assistant_id="assistant_1",
            user_message=ChatEventUserMessage(
                id="user_message_1",
                text="question",
                original_text="question",
                created_at="2026-01-01T00:00:00Z",
                language="EN",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="assistant_message_1",
                created_at="2026-01-01T00:00:00Z",
            ),
            metadata_filter=metadata_filter,
        ),
    )


def _tool_call(call_id: str, **extra_arguments: Any) -> LanguageModelFunction:
    return LanguageModelFunction(
        id=call_id,
        name="InternalSearch",
        arguments={
            "search_string": "gift policy",
            "language": "english",
            **extra_arguments,
        },
    )


@pytest.fixture
def sdk_search() -> Iterator[AsyncMock]:
    """Replace the HTTP calls of one tool run; yields the search mock."""

    async def search(*args: Any, **kwargs: Any) -> list[Any]:
        # Yield to the event loop like a real request, so concurrent runs interleave.
        await asyncio.sleep(0)
        return []

    with (
        patch.object(
            unique_sdk.Search, "create_async", new=AsyncMock(side_effect=search)
        ) as search_mock,
        patch.object(
            unique_sdk.MessageLog,
            "create_async",
            new=AsyncMock(return_value=MESSAGE_LOG),
        ),
        patch.object(
            unique_sdk.MessageLog,
            "update_async",
            new=AsyncMock(return_value=MESSAGE_LOG),
        ),
    ):
        yield search_mock


def _sent_filters(search_mock: AsyncMock) -> list[Any]:
    return [call.kwargs.get("metaDataFilter") for call in search_mock.await_args_list]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_run__ignores_model_metadata_filter__searches_with_space_filter(
    sdk_search: AsyncMock,
) -> None:
    """
    Purpose: A metadata_filter argument written by the model must not replace the space filter.
    Why this matters: Otherwise the agent searches folders that are not selected for the space (UN-28688).
    Setup summary: Space filter on the event, model filter for another folder in the tool call; assert the search request carries the space filter.
    """
    # Arrange
    tool = InternalSearchTool(
        configuration=InternalSearchConfig(), event=_chat_event(SPACE_FILTER)
    )

    # Act
    response = await tool.run(_tool_call("call_1", metadata_filter=OTHER_FOLDER_FILTER))

    # Assert
    assert response.error_message == ""
    assert _sent_filters(sdk_search) == [SPACE_FILTER]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_run__parallel_calls_keep_space_filter__when_one_call_sets_chat_only(
    sdk_search: AsyncMock,
) -> None:
    """
    Purpose: Concurrent runs on one tool instance must all keep the space filter.
    Why this matters: chat-only mode clears the shared content-service filter while it searches; a parallel call must not inherit that.
    Setup summary: Run a chat_only=True call and a normal call concurrently; assert both requests carry the space filter.
    """
    # Arrange
    tool = InternalSearchTool(
        configuration=InternalSearchConfig(), event=_chat_event(SPACE_FILTER)
    )

    # Act
    await asyncio.gather(
        tool.run(_tool_call("call_1", chat_only=True)),
        tool.run(_tool_call("call_2")),
    )

    # Assert
    assert _sent_filters(sdk_search) == [SPACE_FILTER, SPACE_FILTER]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_run__forwards_content_ids__to_search_request(
    sdk_search: AsyncMock,
) -> None:
    """
    Purpose: content_ids from the tool call still restrict the search.
    Why this matters: content_ids is part of the tool schema and is used by UploadedSearch and the RFP agent.
    Setup summary: Tool call with content_ids; assert they reach the search request alongside the space filter.
    """
    # Arrange
    tool = InternalSearchTool(
        configuration=InternalSearchConfig(), event=_chat_event(SPACE_FILTER)
    )

    # Act
    await tool.run(_tool_call("call_1", content_ids=["cont_1", "cont_2"]))

    # Assert
    assert sdk_search.await_args_list[0].kwargs["contentIds"] == ["cont_1", "cont_2"]
    assert _sent_filters(sdk_search) == [SPACE_FILTER]
