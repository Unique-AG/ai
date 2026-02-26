"""Tests for LoopTokenReducer encoder functionality."""

import pytest

from unique_toolkit.agentic.history_manager.loop_token_reducer import LoopTokenReducer
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.app import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelUserMessage,
)


@pytest.mark.ai
def test_loop_token_reducer_get_encoder_with_gpt():
    event = ChatEvent(
        id="test_id",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        company_id="test_company",
        user_id="test_user",
        payload=ChatEventPayload(
            name="test",
            description="test",
            configuration={},
            chat_id="test_chat",
            assistant_id="test_assistant",
            user_message=ChatEventUserMessage(
                id="user_msg_1",
                text="Test",
                original_text="Test",
                created_at="2024-01-01T00:00:00Z",
                language="en",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="asst_msg_1", created_at="2024-01-01T00:00:00Z"
            ),
        ),
    )

    language_model = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_0513
    )
    reference_manager = ReferenceManager()

    reducer = LoopTokenReducer(
        event=event,
        max_history_tokens=1000,
        has_uploaded_content_config=False,
        logger=None,
        reference_manager=reference_manager,
        language_model=language_model,
    )

    encoder = reducer._encoder
    assert callable(encoder)

    tokens = encoder("Hello world")
    assert isinstance(tokens, list)
    assert all(isinstance(t, int) for t in tokens)


@pytest.mark.ai
def test_loop_token_reducer_get_encoder_with_qwen():
    event = ChatEvent(
        id="test_id",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        company_id="test_company",
        user_id="test_user",
        payload=ChatEventPayload(
            name="test",
            description="test",
            configuration={},
            chat_id="test_chat",
            assistant_id="test_assistant",
            user_message=ChatEventUserMessage(
                id="user_msg_1",
                text="Test",
                original_text="Test",
                created_at="2024-01-01T00:00:00Z",
                language="en",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="asst_msg_1", created_at="2024-01-01T00:00:00Z"
            ),
        ),
    )

    language_model = LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)
    reference_manager = ReferenceManager()

    reducer = LoopTokenReducer(
        event=event,
        max_history_tokens=1000,
        has_uploaded_content_config=False,
        logger=None,
        reference_manager=reference_manager,
        language_model=language_model,
    )

    encoder = reducer._encoder
    assert callable(encoder)

    tokens = encoder("你好世界")
    assert isinstance(tokens, list)
    assert all(isinstance(t, int) for t in tokens)


@pytest.mark.ai
def test_loop_token_reducer_count_message_tokens():
    event = ChatEvent(
        id="test_id",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        company_id="test_company",
        user_id="test_user",
        payload=ChatEventPayload(
            name="test",
            description="test",
            configuration={},
            chat_id="test_chat",
            assistant_id="test_assistant",
            user_message=ChatEventUserMessage(
                id="user_msg_1",
                text="Test",
                original_text="Test",
                created_at="2024-01-01T00:00:00Z",
                language="en",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="asst_msg_1", created_at="2024-01-01T00:00:00Z"
            ),
        ),
    )

    language_model = LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)
    reference_manager = ReferenceManager()

    reducer = LoopTokenReducer(
        event=event,
        max_history_tokens=1000,
        has_uploaded_content_config=False,
        logger=None,
        reference_manager=reference_manager,
        language_model=language_model,
    )

    messages = LanguageModelMessages(
        root=[
            LanguageModelUserMessage(content="Hello world"),
            LanguageModelUserMessage(content="How are you?"),
        ]
    )

    token_count = reducer._count_message_tokens(messages)

    assert isinstance(token_count, int)
    assert token_count > 0
