"""
Tests for LoopTokenReducer service.

This file contains tests for the LoopTokenReducer class which manages
token reduction in agentic tool loops.
"""

import json
from logging import Logger
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from unittest.mock import Mock

from unique_toolkit.agentic.history_manager.loop_token_reducer import (
    MAX_INPUT_TOKENS_SAFETY_PERCENTAGE,
    LoopTokenReducer,
    SourceReductionResult,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.app import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)


# Centralized Fixtures
@pytest.fixture
def test_event() -> ChatEvent:
    """
    Purpose: Provide a test ChatEvent for LoopTokenReducer initialization.
    Why this matters: Consistent event structure ensures predictable test behavior.
    Setup summary: Creates event with test user, company, chat, and assistant IDs.
    """
    return ChatEvent(
        id="some-id",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        user_id="test_user",
        company_id="test_company",
        payload=ChatEventPayload(
            assistant_id="test_assistant",
            chat_id="test_chat",
            name="module",
            description="module_description",
            configuration={},
            user_message=ChatEventUserMessage(
                id="user_message_id",
                text="Test user message",
                created_at="2021-01-01T00:00:00Z",
                language="DE",
                original_text="Test user message",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="assistant_message_id", created_at="2021-01-01T00:00:00Z"
            ),
            metadata_filter={},
        ),
    )


@pytest.fixture
def mock_logger() -> Logger:
    """
    Purpose: Provide a mock logger for tests.
    Why this matters: Tests should not produce actual log output.
    """
    return MagicMock(spec=Logger)


@pytest.fixture
def mock_reference_manager() -> ReferenceManager:
    """
    Purpose: Provide a ReferenceManager for tests.
    Why this matters: LoopTokenReducer requires a ReferenceManager instance.
    """
    return ReferenceManager()


@pytest.fixture
def language_model_info() -> LanguageModelInfo:
    """
    Purpose: Provide a LanguageModelInfo for tests.
    Why this matters: LoopTokenReducer requires language model info for token limits.
    """
    return LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_0513)


@pytest.fixture
def loop_token_reducer(
    mock_logger: Logger,
    test_event: ChatEvent,
    mock_reference_manager: ReferenceManager,
    language_model_info: LanguageModelInfo,
) -> LoopTokenReducer:
    """
    Purpose: Provide a LoopTokenReducer instance for testing.
    Why this matters: Centralized reducer creation ensures consistent test setup.
    """
    return LoopTokenReducer(
        logger=mock_logger,
        event=test_event,
        max_history_tokens=4000,
        has_uploaded_content_config=False,
        reference_manager=mock_reference_manager,
        language_model=language_model_info,
    )


def create_content_chunk(
    chunk_id: str,
    text: str,
    content_id: str = "cont_test123",
    order: int = 0,
) -> ContentChunk:
    """Helper function to create ContentChunk instances for testing."""
    return ContentChunk(
        id=content_id,
        chunk_id=chunk_id,
        text=text,
        order=order,
        key="test_file.pdf",
    )


def create_tool_message(
    tool_call_id: str,
    name: str,
    content: str | dict,
) -> LanguageModelToolMessage:
    """Helper function to create LanguageModelToolMessage instances for testing."""
    if isinstance(content, dict):
        content = json.dumps(content)
    return LanguageModelToolMessage(
        tool_call_id=tool_call_id,
        name=name,
        content=content,
    )


# SourceReductionResult Tests
@pytest.mark.ai
def test_source_reduction_result__creates_valid_instance__with_required_fields_AI() -> (
    None
):
    """
    Purpose: Verify SourceReductionResult can be created with all required fields.
    Why this matters: SourceReductionResult is used to track reduction state.
    """
    # Arrange
    message = create_tool_message("tool_1", "TestTool", "content")
    chunks = [create_content_chunk("chunk_1", "text")]

    # Act
    result = SourceReductionResult(
        message=message,
        reduced_chunks=chunks,
        chunk_offset=0,
        source_offset=0,
    )

    # Assert
    assert result.message == message
    assert result.reduced_chunks == chunks
    assert result.chunk_offset == 0
    assert result.source_offset == 0


# Initialization Tests
@pytest.mark.ai
def test_loop_token_reducer__initializes__with_valid_parameters_AI(
    mock_logger: Logger,
    test_event: ChatEvent,
    mock_reference_manager: ReferenceManager,
    language_model_info: LanguageModelInfo,
) -> None:
    """
    Purpose: Verify LoopTokenReducer initializes correctly with valid parameters.
    Why this matters: Proper initialization is required for all reducer operations.
    """
    # Arrange & Act
    reducer = LoopTokenReducer(
        logger=mock_logger,
        event=test_event,
        max_history_tokens=4000,
        has_uploaded_content_config=False,
        reference_manager=mock_reference_manager,
        language_model=language_model_info,
    )

    # Assert
    assert reducer._max_history_tokens == 4000
    assert reducer._has_uploaded_content_config is False
    assert reducer._logger == mock_logger
    assert reducer._reference_manager == mock_reference_manager
    assert reducer._language_model == language_model_info


# Token Limit Tests
@pytest.mark.ai
def test_get_max_tokens__returns_correct_value__with_safety_margin_AI(
    loop_token_reducer: LoopTokenReducer,
    language_model_info: LanguageModelInfo,
) -> None:
    """
    Purpose: Verify _get_max_tokens applies the safety margin correctly.
    Why this matters: Safety margin prevents exceeding actual token limits.
    """
    # Arrange
    expected_max = int(
        language_model_info.token_limits.token_limit_input
        * (1 - MAX_INPUT_TOKENS_SAFETY_PERCENTAGE)
    )

    # Act
    result = loop_token_reducer._get_max_tokens()

    # Assert
    assert result == expected_max


@pytest.mark.ai
def test_exceeds_token_limit__returns_false__when_under_limit_AI(
    loop_token_reducer: LoopTokenReducer,
    mock_reference_manager: ReferenceManager,
) -> None:
    """
    Purpose: Verify _exceeds_token_limit returns False when under limit.
    Why this matters: Should not trigger reduction when not needed.
    """
    # Arrange
    token_count = 100  # Well under any reasonable limit

    # Act
    result = loop_token_reducer._exceeds_token_limit(token_count)

    # Assert
    assert result is False


@pytest.mark.ai
def test_exceeds_token_limit__returns_false__when_no_multiple_chunks_AI(
    loop_token_reducer: LoopTokenReducer,
    mock_reference_manager: ReferenceManager,
) -> None:
    """
    Purpose: Verify _exceeds_token_limit returns False when no tool call has multiple chunks.
    Why this matters: Reduction requires at least one tool call with multiple chunks.
    """
    # Arrange
    # Add a single chunk to the reference manager
    from unique_toolkit.agentic.tools.schemas import ToolCallResponse

    tool_response = ToolCallResponse(
        id="tool_1",
        name="TestTool",
        content="test",
        content_chunks=[create_content_chunk("chunk_1", "text")],
    )
    mock_reference_manager.extract_referenceable_chunks([tool_response])
    token_count = 1_000_000  # Over any limit

    # Act
    result = loop_token_reducer._exceeds_token_limit(token_count)

    # Assert
    assert result is False


@pytest.mark.ai
def test_exceeds_token_limit__returns_true__when_over_limit_with_multiple_chunks_AI(
    loop_token_reducer: LoopTokenReducer,
    mock_reference_manager: ReferenceManager,
) -> None:
    """
    Purpose: Verify _exceeds_token_limit returns True when over limit with multiple chunks.
    Why this matters: Should trigger reduction when needed.
    """
    # Arrange
    from unique_toolkit.agentic.tools.schemas import ToolCallResponse

    # Add multiple chunks to a tool call
    tool_response = ToolCallResponse(
        id="tool_1",
        name="TestTool",
        content="test",
        content_chunks=[
            create_content_chunk("chunk_1", "text1"),
            create_content_chunk("chunk_2", "text2"),
        ],
    )
    mock_reference_manager.extract_referenceable_chunks([tool_response])
    token_count = 1_000_000  # Over any limit

    # Act
    result = loop_token_reducer._exceeds_token_limit(token_count)

    # Assert
    assert result is True


# Overshoot Factor Tests
@pytest.mark.ai
def test_calculate_overshoot_factor__returns_correct_ratio_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _calculate_overshoot_factor computes correct ratio.
    Why this matters: Overshoot factor determines reduction aggressiveness.
    """
    # Arrange
    max_tokens = loop_token_reducer._get_max_tokens()
    token_count = max_tokens * 2  # 2x overshoot

    # Act
    result = loop_token_reducer._calculate_overshoot_factor(token_count)

    # Assert
    assert abs(result - 2.0) < 0.01  # Allow small floating point error


# Message Token Counting Tests
@pytest.mark.ai
def test_count_message_tokens__returns_positive_integer__for_messages_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _count_message_tokens returns positive count for messages.
    Why this matters: Accurate token counting is essential for reduction logic.
    """
    # Arrange
    messages = LanguageModelMessages(
        root=[
            LanguageModelSystemMessage(content="System prompt"),
            LanguageModelUserMessage(content="User question"),
        ]
    )

    # Act
    result = loop_token_reducer._count_message_tokens(messages)

    # Assert
    assert isinstance(result, int)
    assert result > 0


@pytest.mark.ai
def test_count_message_tokens__scales_with_content_length_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _count_message_tokens increases with longer content.
    Why this matters: Token count should reflect actual content size.
    """
    # Arrange
    short_messages = LanguageModelMessages(
        root=[LanguageModelUserMessage(content="Hi")]
    )
    long_messages = LanguageModelMessages(
        root=[LanguageModelUserMessage(content="This is a much longer message " * 100)]
    )

    # Act
    short_count = loop_token_reducer._count_message_tokens(short_messages)
    long_count = loop_token_reducer._count_message_tokens(long_messages)

    # Assert
    assert long_count > short_count


# Message Classification Tests
@pytest.mark.ai
def test_should_reduce_message__returns_true__for_tool_message_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _should_reduce_message identifies tool messages correctly.
    Why this matters: Only tool messages should have their sources reduced.
    """
    # Arrange
    tool_message = create_tool_message("tool_1", "TestTool", "content")

    # Act
    result = loop_token_reducer._should_reduce_message(tool_message)

    # Assert
    assert result is True


@pytest.mark.ai
def test_should_reduce_message__returns_false__for_user_message_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _should_reduce_message excludes user messages.
    Why this matters: User messages should not be reduced.
    """
    # Arrange
    user_message = LanguageModelUserMessage(content="User question")

    # Act
    result = loop_token_reducer._should_reduce_message(user_message)

    # Assert
    assert result is False


@pytest.mark.ai
def test_should_reduce_message__returns_false__for_assistant_message_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _should_reduce_message excludes assistant messages.
    Why this matters: Assistant messages should not be reduced.
    """
    # Arrange
    assistant_message = LanguageModelAssistantMessage(content="Assistant response")

    # Act
    result = loop_token_reducer._should_reduce_message(assistant_message)

    # Assert
    assert result is False


@pytest.mark.ai
def test_should_reduce_message__returns_false__for_system_message_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _should_reduce_message excludes system messages.
    Why this matters: System messages should not be reduced.
    """
    # Arrange
    system_message = LanguageModelSystemMessage(content="System prompt")

    # Act
    result = loop_token_reducer._should_reduce_message(system_message)

    # Assert
    assert result is False


# Source Reduction Tests
@pytest.mark.ai
def test_reduce_sources_in_tool_message__keeps_at_least_one_chunk_AI(
    loop_token_reducer: LoopTokenReducer,
    mock_reference_manager: ReferenceManager,
) -> None:
    """
    Purpose: Verify _reduce_sources_in_tool_message always keeps at least one chunk.
    Why this matters: Even with extreme overshoot, one chunk must remain.
    """
    # Arrange
    from unique_toolkit.agentic.tools.schemas import ToolCallResponse

    tool_message = create_tool_message("tool_1", "TestTool", "content")
    chunks = [
        create_content_chunk("chunk_1", "text1"),
        create_content_chunk("chunk_2", "text2"),
        create_content_chunk("chunk_3", "text3"),
    ]
    tool_response = ToolCallResponse(
        id="tool_1",
        name="TestTool",
        content="test",
        content_chunks=chunks,
    )
    mock_reference_manager.extract_referenceable_chunks([tool_response])

    # Act - Use extreme overshoot factor
    result = loop_token_reducer._reduce_sources_in_tool_message(
        message=tool_message,
        chunk_offset=0,
        source_offset=0,
        overshoot_factor=100.0,  # Extreme overshoot
    )

    # Assert
    assert len(result.reduced_chunks) >= 1


@pytest.mark.ai
def test_reduce_sources_in_tool_message__returns_empty_chunks__for_message_without_chunks_AI(
    loop_token_reducer: LoopTokenReducer,
    mock_reference_manager: ReferenceManager,
) -> None:
    """
    Purpose: Verify _reduce_sources_in_tool_message handles messages without chunks.
    Why this matters: Some tool calls may not have associated content chunks.
    """
    # Arrange
    tool_message = create_tool_message("tool_no_chunks", "TestTool", "content")

    # Act
    result = loop_token_reducer._reduce_sources_in_tool_message(
        message=tool_message,
        chunk_offset=0,
        source_offset=0,
        overshoot_factor=2.0,
    )

    # Assert
    assert result.reduced_chunks == []
    assert result.message == tool_message


# Tool Message Creation Tests
@pytest.mark.ai
def test_create_reduced_empty_sources_message__sets_no_sources_content_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _create_reduced_empty_sources_message creates proper message.
    Why this matters: Empty source messages should have appropriate content.
    """
    # Arrange
    original_message = create_tool_message("tool_1", "TestTool", "original content")

    # Act
    result = loop_token_reducer._create_reduced_empty_sources_message(original_message)

    # Assert
    assert result.content == "No relevant sources found."
    assert result.tool_call_id == "tool_1"
    assert result.name == "TestTool"


@pytest.mark.ai
def test_create_reduced_standard_sources_message__formats_sources_correctly_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _create_reduced_standard_sources_message formats sources as JSON.
    Why this matters: Sources must be properly formatted for LLM consumption.
    """
    # Arrange
    original_message = create_tool_message("tool_1", "TestTool", "original")
    chunks = [
        create_content_chunk("chunk_1", "First chunk text"),
        create_content_chunk("chunk_2", "Second chunk text"),
    ]

    # Act
    result: LanguageModelToolMessage = (
        loop_token_reducer._create_reduced_standard_sources_message(
            message=original_message,
            content_chunks=chunks,
            source_offset=5,
        )
    )

    # Assert
    content = result.content
    assert isinstance(content, str)
    content_dict = json.loads(content)
    assert len(content_dict) == 2
    assert content_dict[0]["source_number"] == 5
    assert content_dict[0]["content"] == "First chunk text"
    assert content_dict[1]["source_number"] == 6
    assert content_dict[1]["content"] == "Second chunk text"


def test_create_reduced_table_search_message__preserves_sql_content_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _create_reduced_table_search_message handles TableSearch specially.
    Why this matters: TableSearch has different content format than other tools.
    """
    # Arrange
    table_content = {"content": "SELECT * FROM users", "other_field": "value"}
    original_message = create_tool_message("tool_1", "TableSearch", table_content)
    chunk = create_content_chunk("chunk_1", "table result")

    # Act
    result = loop_token_reducer._create_reduced_table_search_message(
        message=original_message,
        content_chunks=[chunk],
        source_offset=0,
    )

    # Assert
    content = result.content
    assert isinstance(content, str)
    content_dict = json.loads(content)
    assert content_dict["source_number"] == 0
    assert content_dict["content"] == "SELECT * FROM users"


@pytest.mark.ai
def test_create_reduced_table_search_message__handles_no_chunks_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _create_reduced_table_search_message works with no chunks.
    Why this matters: TableSearch may not always have content chunks.
    """
    # Arrange
    table_content = json.dumps({"content": "SELECT * FROM users"})
    original_message = create_tool_message("tool_1", "TableSearch", table_content)

    # Act
    result = loop_token_reducer._create_reduced_table_search_message(
        message=original_message,
        content_chunks=None,
        source_offset=0,
    )

    # Assert
    assert result.content == original_message.content


# History Construction Tests
@pytest.mark.ai
def test_construct_history__combines_db_and_loop_history_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _construct_history combines histories correctly.
    Why this matters: Final history must include both DB and loop messages.
    """
    # Arrange
    db_history: list[LanguageModelMessage] = [
        LanguageModelSystemMessage(content="System prompt"),
        LanguageModelUserMessage(content="Previous question"),
    ]
    loop_history: list[LanguageModelMessage] = [
        LanguageModelAssistantMessage(content="Current response"),
    ]

    # Act
    result = loop_token_reducer._construct_history(db_history, loop_history)

    # Assert
    assert len(result.root) == 3
    assert result.root[0].content == "System prompt"
    assert result.root[1].content == "Previous question"
    assert result.root[2].content == "Current response"


# Replace User Message Tests
@pytest.mark.ai
def test_replace_user_message__replaces_last_user_message_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _replace_user_message replaces the last user message correctly.
    Why this matters: Rendered user message must replace original in history.
    """
    # Arrange
    history: list[LanguageModelMessage] = [
        LanguageModelSystemMessage(content="System prompt"),
        LanguageModelUserMessage(content="Original question"),
    ]
    original_user_message = "Original question"
    rendered_user_message = "Rendered question with context"

    # Act
    result = loop_token_reducer._replace_user_message(
        history, original_user_message, rendered_user_message
    )

    # Assert
    assert result[-1].content == "Rendered question with context"


@pytest.mark.ai
def test_replace_user_message__adds_user_message__when_last_is_not_user_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _replace_user_message adds message when last is not user.
    Why this matters: Ensures user message is always present at end.
    """
    # Arrange
    history: list[LanguageModelMessage] = [
        LanguageModelSystemMessage(content="System prompt"),
        LanguageModelAssistantMessage(content="Assistant message"),
    ]
    original_user_message = "Original question"
    rendered_user_message = "Rendered question"

    # Act
    result = loop_token_reducer._replace_user_message(
        history, original_user_message, rendered_user_message
    )

    # Assert
    assert len(result) == 3
    assert result[-1].role == LanguageModelMessageRole.USER
    assert result[-1].content == "Rendered question"


# Ensure Last Message is User Tests
@pytest.mark.ai
def test_ensure_last_message_is_user_message__returns_from_first_user_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify ensure_last_message_is_user_message finds first user message.
    Why this matters: History should start from a user message for proper context.
    """
    # Arrange
    history = [
        LanguageModelAssistantMessage(content="Orphan assistant"),
        LanguageModelUserMessage(content="User question"),
        LanguageModelAssistantMessage(content="Response"),
    ]

    # Act
    result = loop_token_reducer.ensure_last_message_is_user_message(history)

    # Assert
    assert len(result) == 2
    assert result[0].role == LanguageModelMessageRole.USER


# Token Window Limiting Tests
@pytest.mark.ai
def test_limit_to_token_window__keeps_recent_messages_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _limit_to_token_window keeps most recent messages.
    Why this matters: Token limiting should prioritize recent context.
    """
    # Arrange
    messages: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="Old message " * 100),
        LanguageModelUserMessage(content="Recent message"),
    ]

    # Act - Very small token limit
    result = loop_token_reducer._limit_to_token_window(messages, token_limit=50)

    # Assert
    assert len(result) >= 1
    assert result[-1].content == "Recent message"


@pytest.mark.ai
def test_limit_to_token_window__returns_empty__when_first_message_exceeds_limit_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _limit_to_token_window handles oversized single message.
    Why this matters: Edge case where even one message exceeds limit.
    """
    # Arrange
    messages: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="Very long message " * 1000),
    ]

    # Act
    result = loop_token_reducer._limit_to_token_window(messages, token_limit=10)

    # Assert
    assert len(result) == 0


# Full Source Reduction Flow Tests
@pytest.mark.ai
def test_reduce_message_length_by_reducing_sources__processes_all_tool_messages_AI(
    loop_token_reducer: LoopTokenReducer,
    mock_reference_manager: ReferenceManager,
) -> None:
    """
    Purpose: Verify full reduction flow processes all tool messages.
    Why this matters: All tool messages should be considered for reduction.
    """
    # Arrange
    from unique_toolkit.agentic.tools.schemas import ToolCallResponse

    # Set up reference manager with chunks for multiple tools
    tool_response_1 = ToolCallResponse(
        id="tool_1",
        name="Search",
        content="test",
        content_chunks=[
            create_content_chunk("chunk_1", "text1"),
            create_content_chunk("chunk_2", "text2"),
        ],
    )
    tool_response_2 = ToolCallResponse(
        id="tool_2",
        name="Search",
        content="test",
        content_chunks=[
            create_content_chunk("chunk_3", "text3"),
        ],
    )
    mock_reference_manager.extract_referenceable_chunks(
        [tool_response_1, tool_response_2]
    )

    history: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="Question"),
        LanguageModelAssistantMessage(content="Let me search"),
        create_tool_message("tool_1", "Search", "original1"),
        create_tool_message("tool_2", "Search", "original2"),
    ]

    # Act
    result = (
        loop_token_reducer._reduce_message_length_by_reducing_sources_in_tool_response(
            history, overshoot_factor=2.0
        )
    )

    # Assert
    assert len(result) == 4
    # Non-tool messages should be unchanged
    assert result[0].content == "Question"
    assert result[1].content == "Let me search"


# Encoder Tests
@pytest.mark.ai
def test_get_encoder__returns_correct_encoder__for_model_AI(
    loop_token_reducer: LoopTokenReducer,
    language_model_info: LanguageModelInfo,
) -> None:
    """
    Purpose: Verify _get_encoder returns correct tiktoken encoder.
    Why this matters: Correct encoder is essential for accurate token counting.
    """
    # Arrange & Act
    encoder = loop_token_reducer._get_encoder(language_model_info)

    # Assert
    assert encoder is not None
    # Verify encoder works by encoding a simple string
    tokens = encoder.encode("Hello world")
    assert len(tokens) > 0


@pytest.mark.ai
def test_get_encoder__uses_default__when_encoder_name_is_none_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _get_encoder uses default when model has no encoder name.
    Why this matters: Fallback to default encoder prevents errors.
    """
    # Arrange
    mock_model = MagicMock()
    mock_model.encoder_name = None

    # Act
    encoder = loop_token_reducer._get_encoder(mock_model)

    # Assert
    assert encoder is not None
    # cl100k_base is the default
    tokens = encoder.encode("Test")
    assert len(tokens) > 0


# Integration-style Tests (still unit tests but test larger flows)
@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.history_manager.loop_token_reducer.get_full_history_with_contents"
)
@patch.object(LoopTokenReducer, "_count_message_tokens")
async def test_get_history_for_model_call__returns_messages__when_under_limit_AI(
    mock_count_tokens: "Mock",
    mock_get_history: "Mock",
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify get_history_for_model_call returns messages when under limit.
    Why this matters: Normal case should return full history without reduction.
    """
    # Arrange
    mock_get_history.return_value = LanguageModelMessages(
        root=[LanguageModelUserMessage(content="Test user message")]
    )
    mock_count_tokens.return_value = 100  # Under limit

    async def mock_remove_from_text(text: str) -> str:
        return text

    # Act
    result = await loop_token_reducer.get_history_for_model_call(
        original_user_message="Test user message",
        rendered_user_message_string="Rendered user message",
        rendered_system_message_string="System prompt",
        loop_history=[],
        remove_from_text=mock_remove_from_text,
    )

    # Assert
    assert isinstance(result, LanguageModelMessages)
    assert len(result.root) > 0
