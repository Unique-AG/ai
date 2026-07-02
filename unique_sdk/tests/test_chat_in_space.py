from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion


@pytest.mark.asyncio
async def test_send_message_and_wait_for_completion__calls_update_hook_for_changed_assistant_messages() -> (
    None
):
    on_message_update = AsyncMock()
    placeholder = {
        "id": "assistant-msg",
        "chatId": "chat-1",
        "role": "ASSISTANT",
        "text": None,
        "originalText": None,
        "completedAt": None,
        "stoppedStreamingAt": None,
        "references": None,
        "assessment": None,
    }
    in_progress = {
        "id": "assistant-msg",
        "chatId": "chat-1",
        "role": "ASSISTANT",
        "text": "partial",
        "originalText": "partial",
        "completedAt": None,
        "stoppedStreamingAt": None,
        "references": None,
        "assessment": None,
    }
    duplicate = {**in_progress}
    completed = {
        **in_progress,
        "text": "final",
        "originalText": "final",
        "completedAt": "2026-01-01T00:00:00Z",
    }

    with (
        patch(
            "unique_sdk.utils.chat_in_space.Space.create_message_async",
            new_callable=AsyncMock,
            return_value={"id": "user-msg", "chatId": "chat-1"},
        ),
        patch(
            "unique_sdk.utils.chat_in_space.Space.get_latest_message_async",
            new_callable=AsyncMock,
            side_effect=[placeholder, in_progress, duplicate, completed],
        ),
        patch(
            "unique_sdk.utils.chat_in_space.Message.retrieve_async",
            new_callable=AsyncMock,
            return_value={"debugInfo": {"trace": "ok"}},
        ),
        patch("unique_sdk.utils.chat_in_space.asyncio.sleep", new_callable=AsyncMock),
    ):
        response = await send_message_and_wait_for_completion(
            user_id="user-1",
            company_id="company-1",
            assistant_id="assistant-1",
            text="hello",
            poll_interval=0.01,
            max_wait=1,
            stop_condition="completedAt",
            on_message_update=on_message_update,
        )

    assert response["text"] == "final"
    assert response["debugInfo"] == {"trace": "ok"}
    assert on_message_update.await_count == 2
    assert on_message_update.await_args_list[0].args == (in_progress,)
    assert on_message_update.await_args_list[1].args == (completed,)


@pytest.mark.asyncio
async def test_send_message_and_wait_for_completion__passes_auto_approve_elicitation() -> (
    None
):
    completed = {
        "id": "assistant-msg",
        "chatId": "chat-1",
        "role": "ASSISTANT",
        "text": "done",
        "originalText": "done",
        "completedAt": "2026-01-01T00:00:00Z",
        "stoppedStreamingAt": "2026-01-01T00:00:00Z",
        "references": None,
        "assessment": None,
    }

    with (
        patch(
            "unique_sdk.utils.chat_in_space.Space.create_message_async",
            new_callable=AsyncMock,
            return_value={"id": "user-msg", "chatId": "chat-1"},
        ) as mock_create_message,
        patch(
            "unique_sdk.utils.chat_in_space.Space.get_latest_message_async",
            new_callable=AsyncMock,
            return_value=completed,
        ),
        patch(
            "unique_sdk.utils.chat_in_space.Message.retrieve_async",
            new_callable=AsyncMock,
            return_value={"debugInfo": None},
        ),
        patch("unique_sdk.utils.chat_in_space.asyncio.sleep", new_callable=AsyncMock),
    ):
        await send_message_and_wait_for_completion(
            user_id="user-1",
            company_id="company-1",
            assistant_id="assistant-1",
            text="hello",
            auto_approve_elicitation=True,
            poll_interval=0.01,
            max_wait=1,
            stop_condition="completedAt",
        )

    mock_create_message.assert_awaited_once()
    assert mock_create_message.await_args.kwargs["autoApproveElicitation"] is True
