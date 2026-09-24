"""Tests for Responses-specific helpers in ``complete_with_references.py``.

Focused on the input-shape narrowing helpers: homogeneity checks and the
``input_messages`` closure's type-guard cascade.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai.types.responses import ResponseInputItemParam

from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.complete_with_references import (
    _is_language_model_messages,
    _is_response_input_items,
    _is_response_output_items,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)


@pytest.mark.ai
def test_AI_is_language_model_messages__requires_every_element_to_be_lm_message():
    """
    Purpose: ``_is_language_model_messages`` must inspect every element, not
      just ``msgs[0]``.
    Why this matters: A first-only check silently mis-narrows a heterogeneous
      list, routing a mixed payload to ``message.to_openai`` which then
      crashes on the dict elements.
    Setup summary: Mixed list (LanguageModelMessageOptions + dict) should
      return False; homogeneous list returns True.
    """
    homogeneous = [
        LanguageModelUserMessage(content="hi"),
        LanguageModelSystemMessage(content="sys"),
    ]
    mixed = [LanguageModelUserMessage(content="hi"), {"role": "user", "content": "x"}]

    assert _is_language_model_messages(homogeneous) is True
    assert _is_language_model_messages(mixed) is False


@pytest.mark.ai
def test_AI_is_response_input_items__requires_every_element_to_be_dict():
    """
    Purpose: ``_is_response_input_items`` must check every element.
    Why this matters: See above — a heterogeneous list that happens to lead
      with a dict would otherwise silently pass and later break on the
      non-dict element.
    Setup summary: Mixed and homogeneous variants.
    """
    homogeneous: list[ResponseInputItemParam] = [
        {"role": "user", "content": "hi"},
        {"role": "system", "content": "x"},
    ]
    mixed: list[ResponseInputItemParam | LanguageModelUserMessage] = [
        {"role": "user", "content": "hi"},
        LanguageModelUserMessage(content="x"),
    ]

    assert _is_response_input_items(homogeneous) is True
    assert _is_response_input_items(mixed) is False


@pytest.mark.ai
def test_AI_is_response_output_items__requires_every_element_to_be_output_model():
    """
    Purpose: ``_is_response_output_items`` must accept homogeneous raw Responses
      output models and reject mixed lists.
    Why this matters: Raw Responses history is part of the public input
      contract, but mixed message shapes should still fail loudly.
    Setup summary: Build a raw SDK output message and assert only the
      homogeneous output-model list is accepted.
    """
    from openai.types.responses.response_output_message import ResponseOutputMessage

    output_message = ResponseOutputMessage.model_construct(
        id="msg_1",
        content=[],
        role="assistant",
        status="completed",
        type="message",
    )
    mixed = [output_message, {"role": "user", "content": "x"}]

    assert _is_response_output_items([output_message]) is True
    assert _is_response_output_items(mixed) is False


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_orchestrator__heterogeneous_messages__raises_type_error():
    """
    Purpose: The ``input_messages`` cascade must raise on a heterogeneous list
      rather than silently falling through to ``[]``.
    Why this matters: The previous dead fall-through quietly produced an
      empty request that the model echoed as an empty response. Raising
      makes the bug loud.
    Setup summary: Build the orchestrator with an injected fake client and
      assert that a mixed messages list raises ``TypeError`` before any
      create call is attempted.
    """
    from unittest.mock import AsyncMock, MagicMock

    from pydantic import SecretStr

    from unique_toolkit.app.unique_settings import (
        AuthContext,
        ChatContext,
        UniqueApi,
        UniqueApp,
        UniqueContext,
        UniqueSettings,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.code_interpreter_event_handler import (
        ResponsesCodeInterpreterEventHandler,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.complete_with_references import (
        ResponsesCompleteWithReferences,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.completed_event_handler import (
        ResponsesCompletedEventHandler,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.stream_event_router import (
        ResponsesStreamEventRouter,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.text_delta_event_handler import (
        ResponsesTextDeltaEventHandler,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.tool_call_event_handler import (
        ResponsesToolCallEventHandler,
    )

    auth = AuthContext(user_id=SecretStr("u"), company_id=SecretStr("c"))
    chat = ChatContext(
        chat_id="chat",
        assistant_id="a",
        last_assistant_message_id="m",
        last_user_message_id="um",
        last_user_message_text="",
    )
    settings = UniqueSettings(auth=auth, app=UniqueApp(), api=UniqueApi())
    settings._context = UniqueContext(auth=auth, chat=chat)

    fake_client = MagicMock()
    fake_client.responses.create = AsyncMock()

    orchestrator = ResponsesCompleteWithReferences(
        settings,
        client=fake_client,
        router=ResponsesStreamEventRouter(
            text_event_handler=ResponsesTextDeltaEventHandler(replacers=[]),
            tool_call_event_handler=ResponsesToolCallEventHandler(),
            completed_event_handler=ResponsesCompletedEventHandler(),
            code_interpreter_event_handler=ResponsesCodeInterpreterEventHandler(),
        ),
        subscribers=(),
    )

    mixed = [LanguageModelUserMessage(content="hi"), {"role": "user", "content": "x"}]

    with pytest.raises(TypeError, match="heterogeneous"):
        await orchestrator.complete_with_references_async(
            model_name="m", messages=mixed
        )

    fake_client.responses.create.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_responses_orchestrator__final_response__includes_request_and_debug_info() -> (
    None
):
    """
    Purpose: Final Responses stream results preserve request and debug
      metadata on the returned assistant message.
    Why this matters: Responses supports richer request shapes than text
      deltas should carry, but the final ``LanguageModelStreamResponse`` still
      needs that metadata for auditing and debugging.
    Setup summary: Drive an empty fake Responses stream with explicit
      ``debug_info`` and assert the returned message contains the final
      request payload and debug data.
    """
    from pydantic import SecretStr

    from unique_toolkit.app.unique_settings import (
        AuthContext,
        ChatContext,
        UniqueApi,
        UniqueApp,
        UniqueContext,
        UniqueSettings,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.code_interpreter_event_handler import (
        ResponsesCodeInterpreterEventHandler,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.complete_with_references import (
        ResponsesCompleteWithReferences,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.completed_event_handler import (
        ResponsesCompletedEventHandler,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.stream_event_router import (
        ResponsesStreamEventRouter,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.text_delta_event_handler import (
        ResponsesTextDeltaEventHandler,
    )
    from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.tool_call_event_handler import (
        ResponsesToolCallEventHandler,
    )

    class _FakeStream:
        def __init__(self, events: list[Any]) -> None:
            self._events = events

        async def __aenter__(self) -> "_FakeStream":
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            return None

        async def __aiter__(self):
            for event in self._events:
                yield event

    auth = AuthContext(user_id=SecretStr("u"), company_id=SecretStr("c"))
    chat = ChatContext(
        chat_id="chat",
        assistant_id="a",
        last_assistant_message_id="m",
        last_user_message_id="um",
        last_user_message_text="",
    )
    settings = UniqueSettings(auth=auth, app=UniqueApp(), api=UniqueApi())
    settings._context = UniqueContext(auth=auth, chat=chat)

    fake_client = MagicMock()
    fake_client.responses.create = AsyncMock(return_value=_FakeStream([]))
    orchestrator = ResponsesCompleteWithReferences(
        settings,
        client=fake_client,
        router=ResponsesStreamEventRouter(
            text_event_handler=ResponsesTextDeltaEventHandler(replacers=[]),
            tool_call_event_handler=ResponsesToolCallEventHandler(),
            completed_event_handler=ResponsesCompletedEventHandler(),
            code_interpreter_event_handler=ResponsesCodeInterpreterEventHandler(),
        ),
        subscribers=(),
    )

    response = await orchestrator.complete_with_references_async(
        model_name="response-model",
        messages="hello",
        debug_info={"trace_id": "responses-1"},
    )

    assert response.message.gpt_request == {
        "model": "response-model",
        "input": "hello",
        "stream": True,
        "temperature": 0,
    }
    assert response.message.debug_info == {"trace_id": "responses-1"}
