from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.utils.chat_in_space import (
    get_message_usage,
    send_message_and_wait_for_completion,
)


class TestGetMessageUsage:
    @pytest.mark.ai
    def test_get_message_usage__present__returns_usage(self) -> None:
        message = {
            "debugInfo": {
                "token_usage": {
                    "completionTokens": 12,
                    "promptTokens": 34,
                    "totalTokens": 46,
                }
            }
        }
        assert get_message_usage(message) == {
            "completionTokens": 12,
            "promptTokens": 34,
            "totalTokens": 46,
        }

    @pytest.mark.ai
    def test_get_message_usage__no_token_usage_key__returns_none(self) -> None:
        message = {"debugInfo": {"execution_time": {"total_time": 1.0}}}
        assert get_message_usage(message) is None

    @pytest.mark.ai
    def test_get_message_usage__debug_info_none__returns_none(self) -> None:
        message = {"debugInfo": None}
        assert get_message_usage(message) is None

    @pytest.mark.ai
    def test_get_message_usage__debug_info_missing__returns_none(self) -> None:
        message = {}
        assert get_message_usage(message) is None


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
        ) as mock_message_retrieve,
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
    # Regression: debugInfo/token_usage is only ever written to the
    # ASSISTANT message, not the user's own message returned by
    # create_message_async ("user-msg") — the re-fetch must use the
    # completed message's own id ("assistant-msg"), not the stale one.
    mock_message_retrieve.assert_awaited_once_with(
        "user-1", "company-1", "assistant-msg", chatId="chat-1"
    )


@pytest.mark.asyncio
async def test_send_message_and_wait_for_completion__debug_info_from_assistant_not_user_message() -> (
    None
):
    """Regression test: previously, the debugInfo re-fetch used `message_id`
    from the initial create_message_async response (the USER's own message),
    silently discarding the completed ASSISTANT message's real debugInfo
    (where token_usage/execution_time actually live). Verify the fix by
    giving the user and assistant messages distinguishable debugInfo and
    asserting the assistant's is the one that survives."""
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

    async def fake_retrieve(user_id, company_id, message_id, chatId):
        if message_id == "user-msg":
            return {"debugInfo": None}
        if message_id == "assistant-msg":
            return {"debugInfo": {"token_usage": {"totalTokens": 46}}}
        raise AssertionError(f"unexpected message_id: {message_id}")

    with (
        patch(
            "unique_sdk.utils.chat_in_space.Space.create_message_async",
            new_callable=AsyncMock,
            return_value={"id": "user-msg", "chatId": "chat-1"},
        ),
        patch(
            "unique_sdk.utils.chat_in_space.Space.get_latest_message_async",
            new_callable=AsyncMock,
            return_value=completed,
        ),
        patch(
            "unique_sdk.utils.chat_in_space.Message.retrieve_async",
            side_effect=fake_retrieve,
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
        )

    assert response["debugInfo"] == {"token_usage": {"totalTokens": 46}}


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
