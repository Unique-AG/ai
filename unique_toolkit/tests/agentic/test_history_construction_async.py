"""Tests for async history construction functions."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    ChatHistoryWithContent,
    ImageContentInclusion,
    _append_element_to_builder_async,
    download_encoded_images_async,
    get_chat_history_with_contents_async,
    get_full_history_with_contents_and_tool_calls_async,
    get_full_history_with_contents_async,
)
from unique_toolkit.chat.schemas import (
    ChatMessage,
    ChatMessageTool,
    ChatMessageToolResponse,
)
from unique_toolkit.chat.schemas import ChatMessageRole as ChatRole
from unique_toolkit.content.schemas import Content
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
)


def _make_user_message():
    msg = MagicMock()
    msg.id = "user_msg_1"
    msg.text = "hello"
    msg.original_text = "hello"
    msg.created_at = datetime(2026, 1, 1, 13, 0).isoformat()
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


def _make_image_content(key="photo.png", content_id="cont_img1"):
    return Content(
        id=content_id,
        key=key,
        created_at=datetime(2026, 1, 1, 11, 55),
    )


def _make_file_content(key="report.pdf", content_id="cont_file1"):
    return Content(
        id=content_id,
        key=key,
        created_at=datetime(2026, 1, 1, 11, 55),
    )


# ---------------------------------------------------------------------------
# get_chat_history_with_contents_async
# ---------------------------------------------------------------------------


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
async def test_get_chat_history_with_contents_async_dedup_user_message():
    """When last history message has same ID as user_message, it should not be duplicated."""
    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    user_msg = _make_user_message()
    chat_history = [
        ChatMessage(
            id=user_msg.id,
            chat_id="chat_1",
            text="hello",
            role=ChatRole.USER,
            gpt_request=None,
            created_at=datetime(2026, 1, 1, 12, 0),
        ),
    ]

    result = await get_chat_history_with_contents_async(
        user_message=user_msg,
        chat_id="chat_1",
        chat_history=chat_history,
        content_service=content_service,
    )

    assert isinstance(result, ChatHistoryWithContent)
    assert len(result.root) == 1


# ---------------------------------------------------------------------------
# download_encoded_images_async
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_download_encoded_images_async():
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"\x89PNG")

    img_content = MagicMock()
    img_content.key = "test.png"
    img_content.id = "img_1"

    with patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_image_content",
        return_value=True,
    ):
        result = await download_encoded_images_async(
            contents=[img_content],
            content_service=content_service,
            chat_id="chat_1",
        )

    assert len(result) == 1
    assert result[0].startswith("data:image/png;base64,")
    content_service.download_content_to_bytes_async.assert_awaited_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_download_encoded_images_async_exception_handled():
    """Exception during download should be caught; result list stays empty."""
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(
        side_effect=RuntimeError("download failed")
    )

    img_content = MagicMock()
    img_content.key = "bad.png"
    img_content.id = "img_2"

    with patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_image_content",
        return_value=True,
    ):
        result = await download_encoded_images_async(
            contents=[img_content],
            content_service=content_service,
            chat_id="chat_1",
        )

    assert result == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_download_encoded_images_async_non_image_skipped():
    """Non-image content should be skipped entirely."""
    content_service = MagicMock()

    non_img = MagicMock()
    non_img.key = "data.csv"
    non_img.id = "cont_1"

    with patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_image_content",
        return_value=False,
    ):
        result = await download_encoded_images_async(
            contents=[non_img],
            content_service=content_service,
            chat_id="chat_1",
        )

    assert result == []


# ---------------------------------------------------------------------------
# _append_element_to_builder_async
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_append_element_to_builder_async_no_contents():
    """Messages without contents take the simple message_append path."""
    from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
        ChatMessageWithContents,
        FileContentSerialization,
    )

    builder = MagicMock()
    msg = ChatMessageWithContents(
        id="m1",
        chat_id="c1",
        text="hello",
        role=ChatRole.USER,
        gpt_request=None,
        created_at=datetime(2026, 1, 1, 12, 0),
        contents=[],
    )

    await _append_element_to_builder_async(
        builder=builder,
        c=msg,
        text="hello",
        include_images=ImageContentInclusion.ALL,
        file_content_serialization_type=FileContentSerialization.NONE,
        content_service=MagicMock(),
        chat_id="c1",
    )

    builder.message_append.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_append_element_to_builder_async_with_file_contents():
    """Messages with file (non-image) contents use message_append with file info."""
    from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
        ChatMessageWithContents,
        FileContentSerialization,
    )

    file_content = _make_file_content()
    builder = MagicMock()
    msg = ChatMessageWithContents(
        id="m1",
        chat_id="c1",
        text="see attached",
        role=ChatRole.USER,
        gpt_request=None,
        created_at=datetime(2026, 1, 1, 12, 0),
        contents=[file_content],
    )

    with (
        patch(
            "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_file_content",
            return_value=True,
        ),
        patch(
            "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_image_content",
            return_value=False,
        ),
    ):
        await _append_element_to_builder_async(
            builder=builder,
            c=msg,
            text="see attached",
            include_images=ImageContentInclusion.ALL,
            file_content_serialization_type=FileContentSerialization.FILE_NAME,
            content_service=MagicMock(),
            chat_id="c1",
        )

    builder.message_append.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_append_element_to_builder_async_with_image_contents():
    """Messages with image contents use image_message_append."""
    from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
        ChatMessageWithContents,
        FileContentSerialization,
    )

    img_content = _make_image_content()
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"\x89PNG")
    builder = MagicMock()

    msg = ChatMessageWithContents(
        id="m1",
        chat_id="c1",
        text="see this image",
        role=ChatRole.USER,
        gpt_request=None,
        created_at=datetime(2026, 1, 1, 12, 0),
        contents=[img_content],
    )

    with (
        patch(
            "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_file_content",
            return_value=False,
        ),
        patch(
            "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_image_content",
            return_value=True,
        ),
    ):
        await _append_element_to_builder_async(
            builder=builder,
            c=msg,
            text="see this image",
            include_images=ImageContentInclusion.ALL,
            file_content_serialization_type=FileContentSerialization.NONE,
            content_service=content_service,
            chat_id="c1",
        )

    builder.image_message_append.assert_called_once()


# ---------------------------------------------------------------------------
# get_full_history_with_contents_async
# ---------------------------------------------------------------------------


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
async def test_get_full_history_with_contents_async_none_text():
    """Assistant messages with text=None and original_text=None should get text=''."""
    chat_service = MagicMock()
    chat_service.get_full_history_async = AsyncMock(
        return_value=[
            ChatMessage(
                id="a1",
                chat_id="chat_1",
                text=None,
                original_text=None,
                role=ChatRole.ASSISTANT,
                gpt_request=None,
                created_at=datetime(2026, 1, 1, 12, 0),
            ),
        ]
    )

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    result = await get_full_history_with_contents_async(
        user_message=_make_user_message(),
        chat_id="chat_1",
        chat_service=chat_service,
        content_service=content_service,
    )

    assert isinstance(result, LanguageModelMessages)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_full_history_with_contents_async_raises_on_null_user_text():
    """User messages with no text should raise ValueError."""
    chat_service = MagicMock()
    chat_service.get_full_history_async = AsyncMock(return_value=[])

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    user_msg = MagicMock()
    user_msg.id = "user_1"
    user_msg.text = None
    user_msg.original_text = None
    user_msg.created_at = datetime(2026, 1, 1, 13, 0).isoformat()

    with pytest.raises(ValueError, match="Content or original_text"):
        await get_full_history_with_contents_async(
            user_message=user_msg,
            chat_id="chat_1",
            chat_service=chat_service,
            content_service=content_service,
        )


# ---------------------------------------------------------------------------
# get_full_history_with_contents_and_tool_calls_async
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_full_history_with_contents_and_tool_calls_async_no_tools():
    chat_service = MagicMock()
    chat_service.get_full_history_async = AsyncMock(return_value=_make_chat_history())
    chat_service.get_message_tools_async = AsyncMock(return_value=[])

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    (
        result,
        max_src,
        src_map,
    ) = await get_full_history_with_contents_and_tool_calls_async(
        user_message=_make_user_message(),
        chat_id="chat_1",
        chat_service=chat_service,
        content_service=content_service,
    )

    assert isinstance(result, LanguageModelMessages)
    assert max_src == -1
    assert src_map == {}
    chat_service.get_full_history_async.assert_awaited_once()
    chat_service.get_message_tools_async.assert_awaited_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_full_history_with_contents_and_tool_calls_async_with_tools():
    """Tool calls with responses produce interleaved assistant+tool messages."""
    chat_history = [
        ChatMessage(
            id="assist_1",
            chat_id="chat_1",
            text="I'll search for that.",
            role=ChatRole.ASSISTANT,
            gpt_request=None,
            created_at=datetime(2026, 1, 1, 12, 0),
        ),
    ]

    tool_call = ChatMessageTool(
        message_id="assist_1",
        function_name="InternalSearch",
        arguments='{"query":"test"}',
        round_index=0,
        sequence_index=0,
        external_tool_call_id="call_abc",
        response=ChatMessageToolResponse(content="search result"),
    )

    chat_service = MagicMock()
    chat_service.get_full_history_async = AsyncMock(return_value=chat_history)
    chat_service.get_message_tools_async = AsyncMock(return_value=[tool_call])

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    (
        result,
        max_src,
        src_map,
    ) = await get_full_history_with_contents_and_tool_calls_async(
        user_message=_make_user_message(),
        chat_id="chat_1",
        chat_service=chat_service,
        content_service=content_service,
    )

    assert isinstance(result, LanguageModelMessages)
    assert len(result.root) >= 2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_tool_calls_async_empty_assistant_text_skipped():
    """Empty assistant message with tool calls should be dropped (line 630)."""
    chat_history = [
        ChatMessage(
            id="assist_empty",
            chat_id="chat_1",
            text="",
            original_text=None,
            role=ChatRole.ASSISTANT,
            gpt_request=None,
            created_at=datetime(2026, 1, 1, 12, 0),
        ),
    ]

    tool_call = ChatMessageTool(
        message_id="assist_empty",
        function_name="SomeTool",
        arguments="{}",
        round_index=0,
        sequence_index=0,
        external_tool_call_id="call_1",
        response=ChatMessageToolResponse(content="tool output"),
    )

    chat_service = MagicMock()
    chat_service.get_full_history_async = AsyncMock(return_value=chat_history)
    chat_service.get_message_tools_async = AsyncMock(return_value=[tool_call])

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    result, _, _ = await get_full_history_with_contents_and_tool_calls_async(
        user_message=_make_user_message(),
        chat_id="chat_1",
        chat_service=chat_service,
        content_service=content_service,
    )

    assert isinstance(result, LanguageModelMessages)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_tool_calls_async_no_response_skipped():
    """Tool calls without response.content should be filtered out."""
    chat_history = [
        ChatMessage(
            id="assist_1",
            chat_id="chat_1",
            text="Let me check.",
            role=ChatRole.ASSISTANT,
            gpt_request=None,
            created_at=datetime(2026, 1, 1, 12, 0),
        ),
    ]

    tool_call_no_response = ChatMessageTool(
        message_id="assist_1",
        function_name="SomeTool",
        arguments="{}",
        round_index=0,
        sequence_index=0,
        external_tool_call_id="call_1",
        response=None,
    )

    chat_service = MagicMock()
    chat_service.get_full_history_async = AsyncMock(return_value=chat_history)
    chat_service.get_message_tools_async = AsyncMock(
        return_value=[tool_call_no_response]
    )

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    result, _, _ = await get_full_history_with_contents_and_tool_calls_async(
        user_message=_make_user_message(),
        chat_id="chat_1",
        chat_service=chat_service,
        content_service=content_service,
    )

    assert isinstance(result, LanguageModelMessages)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_tool_calls_async_exception_in_get_message_tools():
    """Exception during tool loading should be caught, falling back to empty."""
    chat_history = [
        ChatMessage(
            id="assist_1",
            chat_id="chat_1",
            text="hello",
            role=ChatRole.ASSISTANT,
            gpt_request=None,
            created_at=datetime(2026, 1, 1, 12, 0),
        ),
    ]

    chat_service = MagicMock()
    chat_service.get_full_history_async = AsyncMock(return_value=chat_history)
    chat_service.get_message_tools_async = AsyncMock(
        side_effect=RuntimeError("API error")
    )

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    (
        result,
        max_src,
        src_map,
    ) = await get_full_history_with_contents_and_tool_calls_async(
        user_message=_make_user_message(),
        chat_id="chat_1",
        chat_service=chat_service,
        content_service=content_service,
    )

    assert isinstance(result, LanguageModelMessages)
    assert max_src == -1
    assert src_map == {}


@pytest.mark.ai
@pytest.mark.asyncio
async def test_tool_calls_async_multiple_rounds():
    """Tool calls across two rounds should produce correct message sequence."""
    chat_history = [
        ChatMessage(
            id="assist_1",
            chat_id="chat_1",
            text="Final answer.",
            role=ChatRole.ASSISTANT,
            gpt_request=None,
            created_at=datetime(2026, 1, 1, 12, 0),
        ),
    ]

    tc0 = ChatMessageTool(
        message_id="assist_1",
        function_name="ToolA",
        arguments="{}",
        round_index=0,
        sequence_index=0,
        external_tool_call_id="call_r0",
        response=ChatMessageToolResponse(content="result 0"),
    )
    tc1 = ChatMessageTool(
        message_id="assist_1",
        function_name="ToolB",
        arguments="{}",
        round_index=1,
        sequence_index=0,
        external_tool_call_id="call_r1",
        response=ChatMessageToolResponse(content="result 1"),
    )

    chat_service = MagicMock()
    chat_service.get_full_history_async = AsyncMock(return_value=chat_history)
    chat_service.get_message_tools_async = AsyncMock(return_value=[tc0, tc1])

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    result, _, _ = await get_full_history_with_contents_and_tool_calls_async(
        user_message=_make_user_message(),
        chat_id="chat_1",
        chat_service=chat_service,
        content_service=content_service,
    )

    assert isinstance(result, LanguageModelMessages)
    assert len(result.root) >= 4


# ---------------------------------------------------------------------------
# _append_element_to_builder_async — selected_content_ids filtering
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_append_element_to_builder_async_selected_content_ids_filters_images():
    """When selected_content_ids is set, only matching images should be attached."""
    from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
        ChatMessageWithContents,
        FileContentSerialization,
    )

    img_selected = _make_image_content(key="selected.png", content_id="img_sel")
    img_excluded = _make_image_content(key="excluded.png", content_id="img_exc")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"\x89PNG")
    builder = MagicMock()

    msg = ChatMessageWithContents(
        id="m1",
        chat_id="c1",
        text="two images",
        role=ChatRole.USER,
        gpt_request=None,
        created_at=datetime(2026, 1, 1, 12, 0),
        contents=[img_selected, img_excluded],
    )

    with (
        patch(
            "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_file_content",
            return_value=False,
        ),
        patch(
            "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_image_content",
            return_value=True,
        ),
    ):
        await _append_element_to_builder_async(
            builder=builder,
            c=msg,
            text="two images",
            include_images=ImageContentInclusion.ALL,
            file_content_serialization_type=FileContentSerialization.NONE,
            content_service=content_service,
            chat_id="c1",
            selected_content_ids={"img_sel"},
        )

    builder.image_message_append.assert_called_once()
    download_call_args = content_service.download_content_to_bytes_async.call_args_list
    downloaded_ids = [call.kwargs.get("content_id") for call in download_call_args]
    assert "img_sel" in downloaded_ids
    assert "img_exc" not in downloaded_ids


@pytest.mark.ai
@pytest.mark.asyncio
async def test_append_element_to_builder_async_selected_content_ids_empty_excludes_all():
    """When selected_content_ids is an empty set, no images should be attached."""
    from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
        ChatMessageWithContents,
        FileContentSerialization,
    )

    img = _make_image_content(key="photo.png", content_id="img_1")
    builder = MagicMock()

    msg = ChatMessageWithContents(
        id="m1",
        chat_id="c1",
        text="one image",
        role=ChatRole.USER,
        gpt_request=None,
        created_at=datetime(2026, 1, 1, 12, 0),
        contents=[img],
    )

    with (
        patch(
            "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_file_content",
            return_value=False,
        ),
        patch(
            "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_image_content",
            return_value=True,
        ),
    ):
        await _append_element_to_builder_async(
            builder=builder,
            c=msg,
            text="one image",
            include_images=ImageContentInclusion.ALL,
            file_content_serialization_type=FileContentSerialization.NONE,
            content_service=MagicMock(),
            chat_id="c1",
            selected_content_ids=set(),
        )

    builder.image_message_append.assert_not_called()
    builder.message_append.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_append_element_to_builder_async_selected_content_ids_none_includes_all():
    """When selected_content_ids is None (FF disabled), all images are included."""
    from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
        ChatMessageWithContents,
        FileContentSerialization,
    )

    img = _make_image_content(key="photo.png", content_id="img_1")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"\x89PNG")
    builder = MagicMock()

    msg = ChatMessageWithContents(
        id="m1",
        chat_id="c1",
        text="one image",
        role=ChatRole.USER,
        gpt_request=None,
        created_at=datetime(2026, 1, 1, 12, 0),
        contents=[img],
    )

    with (
        patch(
            "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_file_content",
            return_value=False,
        ),
        patch(
            "unique_toolkit.agentic.history_manager.history_construction_with_contents.FileUtils.is_image_content",
            return_value=True,
        ),
    ):
        await _append_element_to_builder_async(
            builder=builder,
            c=msg,
            text="one image",
            include_images=ImageContentInclusion.ALL,
            file_content_serialization_type=FileContentSerialization.NONE,
            content_service=content_service,
            chat_id="c1",
            selected_content_ids=None,
        )

    builder.image_message_append.assert_called_once()
