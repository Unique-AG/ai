from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.utils.chat_in_space import (
    get_message_invocations,
    send_message_and_wait_for_completion,
)

_INVOCATIONS_PAYLOAD = [
    {
        "modelName": "AZURE_GPT_4o_2024_1120",
        "tokenUsage": {
            "completionTokens": 10,
            "promptTokens": 30,
            "totalTokens": 40,
        },
        "source": "main_loop",
    },
    {
        "modelName": "litellm:anthropic-claude-sonnet-4-5",
        "tokenUsage": {
            "completionTokens": 2,
            "promptTokens": 4,
            "totalTokens": 6,
        },
        "source": "hallucination",
    },
]


class TestGetMessageInvocations:
    @pytest.mark.ai
    def test_get_message_invocations__present__returns_entries(self) -> None:
        message = {"debugInfo": {"llm_invocations": _INVOCATIONS_PAYLOAD}}
        invocations = get_message_invocations(message)
        assert len(invocations) == 2
        assert invocations[0]["modelName"] == "AZURE_GPT_4o_2024_1120"
        assert invocations[0]["source"] == "main_loop"
        assert invocations[1]["tokenUsage"]["totalTokens"] == 6

    @pytest.mark.ai
    def test_get_message_invocations__empty_list__returns_empty(self) -> None:
        """An empty list is the real "no usage reported" identity value --
        still returned as-is, not treated as missing."""
        message = {"debugInfo": {"llm_invocations": []}}
        assert get_message_invocations(message) == []

    @pytest.mark.ai
    def test_get_message_invocations__no_llm_invocations_key__returns_empty(
        self,
    ) -> None:
        message = {"debugInfo": {"execution_time": {"total_time": 1.0}}}
        assert get_message_invocations(message) == []

    @pytest.mark.ai
    def test_get_message_invocations__debug_info_none__returns_empty(self) -> None:
        message = {"debugInfo": None}
        assert get_message_invocations(message) == []

    @pytest.mark.ai
    def test_get_message_invocations__debug_info_missing__returns_empty(self) -> None:
        assert get_message_invocations({}) == []

    @pytest.mark.ai
    def test_get_message_invocations__llm_invocations_not_a_list__returns_empty(
        self,
    ) -> None:
        """Guards against a stale/pre-migration debugInfo blob that still has
        the old {"invocations": [...], "totalTokenUsage": {...}} shape."""
        message = {"debugInfo": {"llm_invocations": _INVOCATIONS_PAYLOAD[0]}}
        assert get_message_invocations(message) == []


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
    assert response["triggeringUserMessageId"] == "user-msg"
    assert on_message_update.await_count == 2
    assert on_message_update.await_args_list[0].args == (in_progress,)
    assert on_message_update.await_args_list[1].args == (completed,)
    # debugInfo/llm_invocations is written to the USER message (message_id from
    # create_message_async), not the assistant reply — the re-fetch must use
    # that original id.
    mock_message_retrieve.assert_awaited_once_with(
        "user-1", "company-1", "user-msg", chatId="chat-1"
    )


@pytest.mark.asyncio
async def test_send_message_and_wait_for_completion__waits_for_invocations_to_complete() -> (
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
        ),
        patch(
            "unique_sdk.utils.chat_in_space.Space.get_latest_message_async",
            new_callable=AsyncMock,
            return_value=completed,
        ),
        patch(
            "unique_sdk.utils.chat_in_space.Message.retrieve_async",
            new_callable=AsyncMock,
            side_effect=[
                {"debugInfo": {"llm_invocations": _INVOCATIONS_PAYLOAD}},
                {
                    "debugInfo": {
                        "llm_invocations": _INVOCATIONS_PAYLOAD,
                        "llm_invocations_complete": True,
                    }
                },
            ],
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
            wait_for_invocations=True,
        )

    assert mock_message_retrieve.await_count == 2
    assert response["debugInfo"]["llm_invocations_complete"] is True


@pytest.mark.asyncio
async def test_send_message_and_wait_for_completion__debug_info_from_user_not_assistant_message() -> (
    None
):
    """debugInfo/llm_invocations is written via ChatService.update_debug_info_async(),
    which always targets the USER message (assistant=False in
    _construct_message_modify_params), not the assistant reply. Verify by
    giving the user and assistant messages distinguishable debugInfo and
    asserting the user's is the one that survives."""
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
            return {"debugInfo": {"llm_invocations": {"totalTokens": 46}}}
        if message_id == "assistant-msg":
            return {"debugInfo": None}
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

    assert response["debugInfo"] == {"llm_invocations": {"totalTokens": 46}}


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
