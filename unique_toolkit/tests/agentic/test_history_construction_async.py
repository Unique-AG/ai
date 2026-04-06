"""Tests for async history construction functions."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    ChatHistoryWithContent,
    get_chat_history_with_contents_async,
    get_full_history_with_contents_and_tool_calls_async,
    get_full_history_with_contents_async,
)
from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.chat.schemas import ChatMessageRole as ChatRole
from unique_toolkit.language_model.schemas import LanguageModelMessages


def _make_user_message():
    msg = MagicMock()
    msg.id = "user_msg_1"
    msg.text = "hello"
    msg.original_text = "hello"
    msg.created_at = datetime.now().isoformat()
    return msg


def _make_chat_history():
    return [
        ChatMessage(
            id="msg_1",
            chat_id="chat_1",
            text="hi there",
            role=ChatRole.ASSISTANT,
            gpt_request=None,
            created_at=datetime(2026, 1, 1, 12, 0),
        ),
    ]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_chat_history_with_contents_async():
    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    result = await get_chat_history_with_contents_async(
        user_message=_make_user_message(),
        chat_id="chat_1",
        chat_history=_make_chat_history(),
        content_service=content_service,
    )

    assert isinstance(result, ChatHistoryWithContent)
    content_service.search_contents_async.assert_awaited_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_full_history_with_contents_async():
    chat_service = MagicMock()
    chat_service.get_full_history_async = AsyncMock(return_value=_make_chat_history())

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    result = await get_full_history_with_contents_async(
        user_message=_make_user_message(),
        chat_id="chat_1",
        chat_service=chat_service,
        content_service=content_service,
    )

    assert isinstance(result, LanguageModelMessages)
    assert len(result.root) > 0
    chat_service.get_full_history_async.assert_awaited_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_full_history_with_contents_and_tool_calls_async():
    chat_service = MagicMock()
    chat_service.get_full_history_async = AsyncMock(return_value=_make_chat_history())
    chat_service.get_message_tools_async = AsyncMock(return_value=[])

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    result, max_src, src_map = (
        await get_full_history_with_contents_and_tool_calls_async(
            user_message=_make_user_message(),
            chat_id="chat_1",
            chat_service=chat_service,
            content_service=content_service,
        )
    )

    assert isinstance(result, LanguageModelMessages)
    assert max_src == -1
    assert src_map == {}
    chat_service.get_full_history_async.assert_awaited_once()
    chat_service.get_message_tools_async.assert_awaited_once()
