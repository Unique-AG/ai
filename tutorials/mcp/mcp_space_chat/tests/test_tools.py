"""Tests for the space chat tools (mocked Space API)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.tools import ToolResult
from mcp.types import EmbeddedResource, TextContent
from mcp_space_chat.tools.ask_space import ask_space
from mcp_space_chat.tools.get_space_answer import get_space_answer
from mcp_space_chat.tools.list_spaces import list_spaces
from mcp_space_chat.ui_resource import CHAT_WINDOW_URI

pytestmark = pytest.mark.ai


def _make_settings():
    return MagicMock()


def _patch_resolve(module: str):
    return patch(
        f"mcp_space_chat.tools.{module}.resolve_chat_settings",
        new=AsyncMock(side_effect=lambda s: s),
    )


def _patch_identity(module: str):
    return patch(
        f"mcp_space_chat.tools.{module}.sdk_identity",
        return_value=("user_1", "company_1"),
    )


def _patch_frontend(base_url: str = "https://next.qa.unique.app"):
    mock_settings = MagicMock()
    mock_settings.frontend_base_url_str.return_value = base_url
    return patch(
        "mcp_space_chat.tools.ask_space.McpSpaceChatSettings",
        return_value=mock_settings,
    )


# ── ask_space ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ask_space_returns_embed_url_and_legacy_ui_resource():
    created = {"id": "msg_1", "chatId": "chat_1"}
    with (
        _patch_resolve("ask_space"),
        _patch_identity("ask_space"),
        _patch_frontend(),
        patch(
            "mcp_space_chat.tools.ask_space.Space.create_message_async",
            new=AsyncMock(return_value=created),
        ) as mock_create,
    ):
        result = await ask_space(
            space_id="assistant_abc",
            prompt="Summarize Q1",
            settings=_make_settings(),
        )

    mock_create.assert_awaited_once_with(
        user_id="user_1",
        company_id="company_1",
        assistantId="assistant_abc",
        text="Summarize Q1",
        chatId=None,
    )
    assert isinstance(result, ToolResult)
    assert result.structured_content == {
        "chatId": "chat_1",
        "spaceId": "assistant_abc",
        "messageId": "msg_1",
        "embedUrl": (
            "https://next.qa.unique.app/chat/embed/chat_1?spaceId=assistant_abc"
        ),
        "openUrl": "https://next.qa.unique.app/chat/chat_1",
    }
    assert isinstance(result.content[0], TextContent)
    assert "chat_1" in result.content[0].text
    # Legacy MCP-UI resource for non-MCP-Apps hosts.
    legacy = result.content[1]
    assert isinstance(legacy, EmbeddedResource)
    assert str(legacy.resource.uri) == "ui://space-chat/embed/chat_1"
    assert legacy.resource.mimeType == "text/uri-list"
    assert (
        legacy.resource.text  # type: ignore[union-attr]
        == "https://next.qa.unique.app/chat/embed/chat_1?spaceId=assistant_abc"
    )


@pytest.mark.asyncio
async def test_ask_space_continues_existing_chat():
    created = {"id": "msg_2", "chatId": "chat_1"}
    with (
        _patch_resolve("ask_space"),
        _patch_identity("ask_space"),
        _patch_frontend(),
        patch(
            "mcp_space_chat.tools.ask_space.Space.create_message_async",
            new=AsyncMock(return_value=created),
        ) as mock_create,
    ):
        result = await ask_space(
            space_id="assistant_abc",
            prompt="And Q2?",
            chat_id="chat_1",
            settings=_make_settings(),
        )

    assert mock_create.await_args is not None
    assert mock_create.await_args.kwargs["chatId"] == "chat_1"
    assert result.structured_content is not None
    assert result.structured_content["chatId"] == "chat_1"


@pytest.mark.asyncio
async def test_ask_space_returns_error_result_on_api_failure():
    with (
        _patch_resolve("ask_space"),
        _patch_identity("ask_space"),
        patch(
            "mcp_space_chat.tools.ask_space.Space.create_message_async",
            new=AsyncMock(side_effect=RuntimeError("space unavailable")),
        ),
    ):
        result = await ask_space(
            space_id="assistant_abc",
            prompt="hello",
            settings=_make_settings(),
        )

    assert result.is_error is True
    assert "space unavailable" in result.content[0].text  # type: ignore[union-attr]


def test_ask_space_tool_meta_links_chat_window_resource():
    from mcp_space_chat.tools.ask_space import _META

    assert _META["ui"] == {"resourceUri": CHAT_WINDOW_URI}
    assert _META["ui/resourceUri"] == CHAT_WINDOW_URI


# ── peek_space_answer ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_peek_space_answer_returns_history_oldest_first():
    from mcp_space_chat.tools.peek_space_answer import peek_space_answer

    history = {
        "messages": [
            {
                "id": "msg_2",
                "role": "ASSISTANT",
                "text": "partial answer",
                "createdAt": "2026-01-01T00:00:02Z",
                "startedStreamingAt": "2026-01-01T00:00:01Z",
                "stoppedStreamingAt": None,
                "references": [
                    {
                        "name": "doc.pdf",
                        "url": "https://example.com/doc.pdf",
                        "sequenceNumber": 1,
                        "sourceId": "src_1",
                        "source": "content",
                    }
                ],
            },
            {
                "id": "msg_1",
                "role": "USER",
                "text": "hello",
                "createdAt": "2026-01-01T00:00:00Z",
                "stoppedStreamingAt": "2026-01-01T00:00:00Z",
                "references": None,
            },
        ],
        "totalCount": 2,
    }
    with (
        _patch_resolve("peek_space_answer"),
        _patch_identity("peek_space_answer"),
        patch(
            "mcp_space_chat.tools.peek_space_answer.Space.get_chat_messages_async",
            new=AsyncMock(return_value=history),
        ) as mock_get,
    ):
        result = await peek_space_answer(
            chat_id="chat_1",
            settings=_make_settings(),
        )

    mock_get.assert_awaited_once_with(
        "user_1", "company_1", "chat_1", take=50
    )
    assert result.is_error is not True
    assert result.structured_content is not None
    assert result.structured_content["done"] is False
    assert result.structured_content["text"] == "partial answer"
    messages = result.structured_content["messages"]
    assert [m["id"] for m in messages] == ["msg_1", "msg_2"]
    assert messages[0]["role"] == "USER"
    assert messages[0]["done"] is True
    assert messages[1]["role"] == "ASSISTANT"
    assert messages[1]["done"] is False
    assert messages[1]["references"][0]["name"] == "doc.pdf"
    assert messages[1]["references"][0]["sequenceNumber"] == 1
    assert messages[1]["logs"] == []


@pytest.mark.asyncio
async def test_peek_space_answer_passes_through_message_logs():
    from mcp_space_chat.tools.peek_space_answer import peek_space_answer

    history = {
        "messages": [
            {
                "id": "msg_1",
                "role": "ASSISTANT",
                "text": "working on it",
                "createdAt": "2026-01-01T00:00:01Z",
                "stoppedStreamingAt": None,
                "references": [],
                "messageLogs": [
                    {
                        "text": "**Loaded Skill**",
                        "status": "COMPLETED",
                        "order": 2,
                        "details": {
                            "data": [
                                {"type": "ToolCall", "text": "pptx"},
                                {
                                    "type": "Todo",
                                    "text": "Set up project",
                                    "status": "done",
                                },
                            ]
                        },
                    },
                    {
                        "text": "**Thinking**",
                        "status": "RUNNING",
                        "order": 1,
                        "details": None,
                    },
                ],
            },
        ],
        "totalCount": 1,
    }
    with (
        _patch_resolve("peek_space_answer"),
        _patch_identity("peek_space_answer"),
        patch(
            "mcp_space_chat.tools.peek_space_answer.Space.get_chat_messages_async",
            new=AsyncMock(return_value=history),
        ),
    ):
        result = await peek_space_answer(
            chat_id="chat_1",
            settings=_make_settings(),
        )

    logs = result.structured_content["messages"][0]["logs"]
    # Sorted by order: Thinking (1) before Loaded Skill (2).
    assert [entry["text"] for entry in logs] == ["**Thinking**", "**Loaded Skill**"]
    assert logs[1]["events"] == [
        {"type": "ToolCall", "text": "pptx", "status": None},
        {"type": "Todo", "text": "Set up project", "status": "done"},
    ]


@pytest.mark.asyncio
async def test_peek_space_answer_marks_done_when_assistant_finished():
    from mcp_space_chat.tools.peek_space_answer import peek_space_answer

    history = {
        "messages": [
            {
                "id": "msg_2",
                "role": "ASSISTANT",
                "text": "final",
                "createdAt": "2026-01-01T00:00:02Z",
                "stoppedStreamingAt": "2026-01-01T00:00:03Z",
                "references": [],
            },
            {
                "id": "msg_1",
                "role": "USER",
                "text": "hello",
                "createdAt": "2026-01-01T00:00:00Z",
                "references": [],
            },
        ],
        "totalCount": 2,
    }
    with (
        _patch_resolve("peek_space_answer"),
        _patch_identity("peek_space_answer"),
        patch(
            "mcp_space_chat.tools.peek_space_answer.Space.get_chat_messages_async",
            new=AsyncMock(return_value=history),
        ),
    ):
        result = await peek_space_answer(
            chat_id="chat_1",
            settings=_make_settings(),
        )

    assert result.structured_content["done"] is True
    assert result.structured_content["text"] == "final"


@pytest.mark.asyncio
async def test_peek_space_answer_returns_error_result_on_api_failure():
    from mcp_space_chat.tools.peek_space_answer import peek_space_answer

    with (
        _patch_resolve("peek_space_answer"),
        _patch_identity("peek_space_answer"),
        patch(
            "mcp_space_chat.tools.peek_space_answer.Space.get_chat_messages_async",
            new=AsyncMock(side_effect=RuntimeError("history unavailable")),
        ),
    ):
        result = await peek_space_answer(
            chat_id="chat_1",
            settings=_make_settings(),
        )

    assert result.is_error is True
    assert "history unavailable" in result.content[0].text  # type: ignore[union-attr]


# ── show_hello_world ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_show_hello_world_returns_legacy_html_and_size_hints():
    from mcp_space_chat.tools.show_hello_world import show_hello_world
    from mcp_space_chat.ui_resource import (
        HELLO_WORLD_HEIGHT_PX,
        HELLO_WORLD_URI,
        HELLO_WORLD_WIDTH_PX,
    )

    result = await show_hello_world(message="Smoke test")

    assert result.is_error is not True
    assert "560" in result.content[0].text  # type: ignore[union-attr]
    assert isinstance(result.content[1], EmbeddedResource)
    assert result.structured_content["preferredWidthPx"] == HELLO_WORLD_WIDTH_PX
    assert result.structured_content["preferredHeightPx"] == HELLO_WORLD_HEIGHT_PX
    assert result.structured_content["resourceUri"] == HELLO_WORLD_URI


def test_show_hello_world_tool_meta_links_hello_resource():
    from mcp_space_chat.tools.show_hello_world import _META
    from mcp_space_chat.ui_resource import HELLO_WORLD_URI

    assert _META["ui"] == {"resourceUri": HELLO_WORLD_URI}


# ── get_space_answer ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_space_answer_polls_until_streaming_stops():
    streaming = {"role": "ASSISTANT", "text": "part", "stoppedStreamingAt": None}
    done = {
        "id": "msg_9",
        "role": "ASSISTANT",
        "text": "final answer",
        "stoppedStreamingAt": "2026-01-01T00:00:00Z",
        "references": [{"name": "doc.pdf"}],
    }
    with (
        _patch_resolve("get_space_answer"),
        _patch_identity("get_space_answer"),
        patch(
            "mcp_space_chat.tools.get_space_answer.Space.get_latest_message_async",
            new=AsyncMock(side_effect=[streaming, done]),
        ),
        patch(
            "mcp_space_chat.tools.get_space_answer.asyncio.sleep",
            new=AsyncMock(),
        ),
    ):
        result = await get_space_answer(
            chat_id="chat_1",
            settings=_make_settings(),
        )

    assert result.is_error is False
    assert result.content[0].text == "final answer"  # type: ignore[union-attr]
    assert result.structured_content == {
        "chatId": "chat_1",
        "messageId": "msg_9",
        "text": "final answer",
        "references": [{"name": "doc.pdf"}],
    }


@pytest.mark.asyncio
async def test_get_space_answer_ignores_user_messages():
    user_message = {
        "role": "USER",
        "text": "prompt",
        "stoppedStreamingAt": "2026-01-01T00:00:00Z",
    }
    done = {
        "id": "msg_9",
        "role": "ASSISTANT",
        "text": "answer",
        "stoppedStreamingAt": "2026-01-01T00:00:01Z",
    }
    with (
        _patch_resolve("get_space_answer"),
        _patch_identity("get_space_answer"),
        patch(
            "mcp_space_chat.tools.get_space_answer.Space.get_latest_message_async",
            new=AsyncMock(side_effect=[user_message, done]),
        ),
        patch(
            "mcp_space_chat.tools.get_space_answer.asyncio.sleep",
            new=AsyncMock(),
        ),
    ):
        result = await get_space_answer(
            chat_id="chat_1",
            settings=_make_settings(),
        )

    assert result.content[0].text == "answer"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_get_space_answer_times_out_with_error_result():
    streaming = {"role": "ASSISTANT", "text": "part", "stoppedStreamingAt": None}
    with (
        _patch_resolve("get_space_answer"),
        _patch_identity("get_space_answer"),
        patch(
            "mcp_space_chat.tools.get_space_answer.Space.get_latest_message_async",
            new=AsyncMock(return_value=streaming),
        ),
        patch(
            "mcp_space_chat.tools.get_space_answer.asyncio.sleep",
            new=AsyncMock(),
        ),
    ):
        result = await get_space_answer(
            chat_id="chat_1",
            max_wait=3.0,
            settings=_make_settings(),
        )

    assert result.is_error is True
    assert "did not finish" in result.content[0].text  # type: ignore[union-attr]


# ── list_spaces ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_spaces_returns_ids_and_names():
    spaces = {
        "data": [
            {
                "id": "assistant_a",
                "name": "research",
                "title": "Research",
                "explanation": "Deep research agent",
            },
            {"id": "assistant_b", "name": "legal", "title": None, "explanation": None},
        ]
    }
    with (
        _patch_resolve("list_spaces"),
        _patch_identity("list_spaces"),
        patch(
            "mcp_space_chat.tools.list_spaces.Space.get_spaces_async",
            new=AsyncMock(return_value=spaces),
        ) as mock_get,
    ):
        result = await list_spaces(settings=_make_settings())

    mock_get.assert_awaited_once_with(
        user_id="user_1", company_id="company_1", name=None, take=100
    )
    text = result.content[0].text  # type: ignore[union-attr]
    assert "assistant_a" in text
    assert "Research" in text
    assert "assistant_b" in text
    assert result.structured_content is not None
    assert len(result.structured_content["spaces"]) == 2


@pytest.mark.asyncio
async def test_list_spaces_handles_empty_result():
    with (
        _patch_resolve("list_spaces"),
        _patch_identity("list_spaces"),
        patch(
            "mcp_space_chat.tools.list_spaces.Space.get_spaces_async",
            new=AsyncMock(return_value={"data": []}),
        ),
    ):
        result = await list_spaces(settings=_make_settings())

    assert result.content[0].text == "No spaces found."  # type: ignore[union-attr]
    assert result.structured_content == {"spaces": []}


@pytest.mark.asyncio
async def test_list_spaces_returns_error_result_on_api_failure():
    with (
        _patch_resolve("list_spaces"),
        _patch_identity("list_spaces"),
        patch(
            "mcp_space_chat.tools.list_spaces.Space.get_spaces_async",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
    ):
        result = await list_spaces(settings=_make_settings())

    assert result.is_error is True
