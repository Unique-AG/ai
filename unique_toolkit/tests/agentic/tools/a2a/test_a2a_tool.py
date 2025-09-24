# AI Generated
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.agentic.tools.a2a.config import SubAgentToolConfig
from unique_toolkit.agentic.tools.a2a.service import SubAgentTool
from unique_toolkit.language_model.schemas import LanguageModelFunction
from tests.test_obj_factory import get_event_obj


@pytest.mark.asyncio
async def test_a2a_tool_passes_tool_choices_to_sdk(monkeypatch):
    event = get_event_obj(
        user_id="u1",
        company_id="c1",
        assistant_id="assistant-1",
        chat_id="chat-1",
    )

    cfg = SubAgentToolConfig(
        name="SubAgentTool",
        assistant_id="assistant-1",
        tool_choices=["WebSearch", "InternalSearch"],
        reuse_chat=False,
        poll_interval=0.01,
        max_wait=0.05,
    )

    # Mock SDK call
    mock_response = {"chatId": "chat-1", "text": "ok"}

    async def fake_send_message_and_wait_for_completion(*args, **kwargs):
        assert kwargs.get("tool_choices") == ["WebSearch", "InternalSearch"]
        return mock_response

    with patch(
        "unique_toolkit.agentic.tools.a2a.service.send_message_and_wait_for_completion",
        new=fake_send_message_and_wait_for_completion,
    ):
        tool = SubAgentTool(configuration=cfg, event=event)
        tool_call = LanguageModelFunction(
            name="SubAgentTool", arguments={"user_message": "hi"}
        )
        result = await tool.run(tool_call)
        assert result.content == "ok"


@pytest.mark.asyncio
async def test_a2a_tool_omits_empty_tool_choices(monkeypatch):
    event = get_event_obj(
        user_id="u1",
        company_id="c1",
        assistant_id="assistant-1",
        chat_id="chat-1",
    )

    cfg = SubAgentToolConfig(
        name="SubAgentTool",
        assistant_id="assistant-1",
        tool_choices=[],
        reuse_chat=False,
        poll_interval=0.01,
        max_wait=0.05,
    )

    mock_response = {"chatId": "chat-1", "text": "ok"}

    async def fake_send_message_and_wait_for_completion(*args, **kwargs):
        # When empty, we expect None to be passed (backward compatible)
        assert kwargs.get("tool_choices") is None
        return mock_response

    with patch(
        "unique_toolkit.agentic.tools.a2a.service.send_message_and_wait_for_completion",
        new=fake_send_message_and_wait_for_completion,
    ):
        tool = SubAgentTool(configuration=cfg, event=event)
        tool_call = LanguageModelFunction(
            name="SubAgentTool", arguments={"user_message": "hi"}
        )
        result = await tool.run(tool_call)
        assert result.content == "ok"
