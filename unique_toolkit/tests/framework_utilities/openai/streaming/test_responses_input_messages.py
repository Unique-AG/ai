"""Tests for Responses-specific helpers in ``complete_with_references.py``.

Focused on the input-shape narrowing helpers: homogeneity checks and the
``input_messages`` closure's type-guard cascade.
"""

from __future__ import annotations

import pytest

from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.complete_with_references import (
    _is_language_model_messages,
    _is_response_input_items,
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
    homogeneous = [
        {"role": "user", "content": "hi"},
        {"role": "system", "content": "x"},
    ]
    mixed = [{"role": "user", "content": "hi"}, LanguageModelUserMessage(content="x")]

    assert _is_response_input_items(homogeneous) is True
    assert _is_response_input_items(mixed) is False


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
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.code_interpreter_handler import (
        ResponsesCodeInterpreterHandler,
    )
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.complete_with_references import (
        ResponsesCompleteWithReferences,
    )
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.completed_handler import (
        ResponsesCompletedHandler,
    )
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.stream_event_router import (
        ResponsesStreamEventRouter,
    )
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.text_delta_handler import (
        ResponsesTextDeltaHandler,
    )
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.tool_call_handler import (
        ResponsesToolCallHandler,
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
            text_handler=ResponsesTextDeltaHandler(replacers=[]),
            tool_call_handler=ResponsesToolCallHandler(),
            completed_handler=ResponsesCompletedHandler(),
            code_interpreter_handler=ResponsesCodeInterpreterHandler(),
        ),
        subscribers=(),
    )

    mixed = [LanguageModelUserMessage(content="hi"), {"role": "user", "content": "x"}]

    with pytest.raises(TypeError, match="heterogeneous"):
        await orchestrator.complete_with_references_async(
            model_name="m", messages=mixed
        )

    fake_client.responses.create.assert_not_called()
