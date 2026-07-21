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
    MIN_PLAIN_TEXT_CHARS_TO_KEEP,
    PLAIN_TEXT_TRUNCATION_MARKER,
    LoopTokenReducer,
    SourceReductionResult,
    _truncate_plain_text,
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
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelFunctionCall,
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
        reference_manager=mock_reference_manager,
        language_model=language_model_info,
    )

    # Assert
    assert reducer._max_history_tokens == 4000
    assert reducer._file_content_serializer is None
    assert reducer._logger == mock_logger
    assert reducer._reference_manager == mock_reference_manager
    assert reducer._language_model == language_model_info


# Token Limit Tests
@pytest.mark.ai
def test_effective_token_limit__returns_correct_value__with_safety_margin_AI(
    loop_token_reducer: LoopTokenReducer,
    language_model_info: LanguageModelInfo,
) -> None:
    """
    Purpose: Verify _effective_token_limit applies the safety margin correctly.
    Why this matters: Safety margin prevents exceeding actual token limits.
    """
    # Arrange
    expected_max = int(
        language_model_info.token_limits.token_limit_input
        * (1 - MAX_INPUT_TOKENS_SAFETY_PERCENTAGE)
    )

    # Act
    result = loop_token_reducer._effective_token_limit

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
def test_exceeds_token_limit__returns_true__when_over_limit_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _exceeds_token_limit is a pure size check.
    Why this matters: Reducibility is a separate concern (_can_reduce_history), so
    the size check must not depend on what sources or messages exist.
    """
    # Arrange
    token_count = 1_000_000  # Over any limit

    # Act
    result = loop_token_reducer._exceeds_token_limit(token_count)

    # Assert
    assert result is True


@pytest.mark.ai
def test_can_reduce_history__returns_false__when_single_chunk_and_no_plain_text_AI(
    loop_token_reducer: LoopTokenReducer,
    mock_reference_manager: ReferenceManager,
) -> None:
    """
    Purpose: Verify _can_reduce_history is False when nothing can be reduced.
    Why this matters: A tool call with a single chunk cannot shed sources, and a
    short plain-text response is below the truncation floor.
    """
    # Arrange
    from unique_toolkit.agentic.tools.schemas import ToolCallResponse

    tool_response = ToolCallResponse(
        id="tool_1",
        name="TestTool",
        content="test",
        content_chunks=[create_content_chunk("chunk_1", "text")],
    )
    mock_reference_manager.extract_referenceable_chunks([tool_response])

    # Act
    result = loop_token_reducer._can_reduce_history([])

    # Assert
    assert result is False


@pytest.mark.ai
def test_can_reduce_history__returns_true__when_multiple_chunks_AI(
    loop_token_reducer: LoopTokenReducer,
    mock_reference_manager: ReferenceManager,
) -> None:
    """
    Purpose: Verify _can_reduce_history is True when a tool call has multiple chunks.
    Why this matters: Sources can still be dropped, so reduction should proceed.
    """
    # Arrange
    from unique_toolkit.agentic.tools.schemas import ToolCallResponse

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

    # Act
    result = loop_token_reducer._can_reduce_history([])

    # Assert
    assert result is True


@pytest.mark.ai
def test_can_reduce_history__returns_true__when_reducible_plain_text_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _can_reduce_history is True for a large chunk-less plain-text
    tool response, even with no chunks registered anywhere.
    Why this matters: Plain-text truncation is an independent reduction lever.
    """
    # Arrange
    message = create_tool_message(
        "tool_1", "TestTool", "x" * (MIN_PLAIN_TEXT_CHARS_TO_KEEP + 100)
    )

    # Act
    result = loop_token_reducer._can_reduce_history([message])

    # Assert
    assert result is True


# Plain-text truncation tests
@pytest.mark.ai
def test_truncate_plain_text__keeps_head_and_appends_marker__when_over_AI() -> None:
    """
    Purpose: Verify _truncate_plain_text keeps the head and appends the marker.
    Why this matters: The truncated content must stay a prefix of the original
    plus a clear marker so the model knows the response was cut.
    """
    # Arrange
    text = "A" * 10_000

    # Act
    result = _truncate_plain_text(text, overshoot_factor=2.0)

    # Assert
    assert result.endswith(PLAIN_TEXT_TRUNCATION_MARKER)
    body = result.removesuffix(PLAIN_TEXT_TRUNCATION_MARKER)
    assert len(body) < len(text)
    assert text.startswith(body)  # only the head is kept


@pytest.mark.ai
def test_truncate_plain_text__returns_unchanged__when_at_or_below_floor_AI() -> None:
    """
    Purpose: Verify text at/below the floor is returned unchanged (no marker).
    Why this matters: Tiny responses must not be shrunk further or marker-stacked.
    """
    # Arrange
    text = "A" * (MIN_PLAIN_TEXT_CHARS_TO_KEEP - 1)

    # Act
    result = _truncate_plain_text(text, overshoot_factor=100.0)

    # Assert
    assert result == text


@pytest.mark.ai
def test_truncate_plain_text__never_below_floor__for_huge_overshoot_AI() -> None:
    """
    Purpose: Verify truncation never keeps fewer than the floor of characters.
    Why this matters: Even under extreme overshoot we retain useful content.
    """
    # Arrange
    text = "A" * 10_000

    # Act
    result = _truncate_plain_text(text, overshoot_factor=1_000.0)

    # Assert
    body = result.removesuffix(PLAIN_TEXT_TRUNCATION_MARKER)
    assert len(body) == MIN_PLAIN_TEXT_CHARS_TO_KEEP


@pytest.mark.ai
def test_truncate_plain_text__does_not_stack_markers__on_repeated_calls_AI() -> None:
    """
    Purpose: Verify a prior marker is stripped before re-truncating.
    Why this matters: The outer loop re-truncates the same message across rounds;
    markers must not accumulate and length must be measured on real content.
    """
    # Arrange
    text = "A" * 10_000

    # Act
    once = _truncate_plain_text(text, overshoot_factor=2.0)
    twice = _truncate_plain_text(once, overshoot_factor=4.0)

    # Assert
    assert twice.count(PLAIN_TEXT_TRUNCATION_MARKER) == 1
    body = twice.removesuffix(PLAIN_TEXT_TRUNCATION_MARKER)
    assert len(body) < len(once.removesuffix(PLAIN_TEXT_TRUNCATION_MARKER))


@pytest.mark.ai
def test_can_truncate_message__true__for_large_chunkless_plain_text_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _can_truncate_message accepts a large chunk-less tool response.
    """
    # Arrange
    message = create_tool_message(
        "tool_1", "TestTool", "x" * (MIN_PLAIN_TEXT_CHARS_TO_KEEP + 1)
    )

    # Act & Assert
    assert loop_token_reducer._can_truncate_message(message) is True


@pytest.mark.ai
def test_can_truncate_message__false__for_table_search_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify TableSearch is excluded from plain-text truncation.
    Why this matters: TableSearch content is structured JSON that truncation
    would corrupt.
    """
    # Arrange
    message = create_tool_message(
        "tool_1", "TableSearch", "x" * (MIN_PLAIN_TEXT_CHARS_TO_KEEP + 1)
    )

    # Act & Assert
    assert loop_token_reducer._can_truncate_message(message) is False


@pytest.mark.ai
def test_can_truncate_message__false__when_below_floor_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify a short chunk-less response is not flagged as truncatable.
    """
    # Arrange
    message = create_tool_message(
        "tool_1", "TestTool", "x" * (MIN_PLAIN_TEXT_CHARS_TO_KEEP - 1)
    )

    # Act & Assert
    assert loop_token_reducer._can_truncate_message(message) is False


@pytest.mark.ai
def test_can_truncate_message__false__when_message_has_chunks_AI(
    loop_token_reducer: LoopTokenReducer,
    mock_reference_manager: ReferenceManager,
) -> None:
    """
    Purpose: Verify a chunk-bearing tool response is reduced via sources, not
    plain-text truncation.
    """
    # Arrange
    from unique_toolkit.agentic.tools.schemas import ToolCallResponse

    mock_reference_manager.extract_referenceable_chunks(
        [
            ToolCallResponse(
                id="tool_1",
                name="TestTool",
                content="test",
                content_chunks=[
                    create_content_chunk("chunk_1", "text1"),
                    create_content_chunk("chunk_2", "text2"),
                ],
            )
        ]
    )
    message = create_tool_message(
        "tool_1", "TestTool", "x" * (MIN_PLAIN_TEXT_CHARS_TO_KEEP + 1)
    )

    # Act & Assert
    assert loop_token_reducer._can_truncate_message(message) is False


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
def test_reduce_sources_in_tool_message__reduces_chunks__with_small_overshoot_factor_AI(
    loop_token_reducer: LoopTokenReducer,
    mock_reference_manager: ReferenceManager,
) -> None:
    """
    Purpose: Verify _reduce_sources_in_tool_message reduces chunks even with small overshoot.
    Why this matters: When overshoot_factor is between 1.0 and ~1.33, the algorithm must still
    reduce chunks. Previously, the formula `num_sources / (overshoot_factor * 0.75)` would
    yield more chunks than num_sources when overshoot_factor * 0.75 < 1.0, preventing reduction.
    """
    # Arrange
    from unique_toolkit.agentic.tools.schemas import ToolCallResponse

    tool_message = create_tool_message("tool_1", "TestTool", "content")
    chunks = [create_content_chunk(f"chunk_{i}", f"text{i}") for i in range(10)]
    tool_response = ToolCallResponse(
        id="tool_1",
        name="TestTool",
        content="test",
        content_chunks=chunks,
    )
    mock_reference_manager.extract_referenceable_chunks([tool_response])

    # Act - Use overshoot factor between 1.0 and 1.33 where old formula would fail
    # With overshoot_factor=1.2: old formula gives int(10 / 0.9) = 11 (no reduction!)
    # With fix: int(10 / 1.2) = 8 (proper reduction)
    result = loop_token_reducer._reduce_sources_in_tool_message(
        message=tool_message,
        chunk_offset=0,
        source_offset=0,
        overshoot_factor=1.2,
    )

    # Assert - Should reduce from 10 to 8 chunks
    assert len(result.reduced_chunks) < 10
    assert len(result.reduced_chunks) == 8


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
    assert content_dict[0]["content_id"] == "cont_test123"
    assert content_dict[0]["content"] == "First chunk text"
    assert content_dict[1]["source_number"] == 6
    assert content_dict[1]["content_id"] == "cont_test123"
    assert content_dict[1]["content"] == "Second chunk text"


@pytest.mark.ai
def test_create_reduced_standard_sources_message__preserves_readable_unicode_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify reduced source messages keep multilingual text readable.
    Why this matters: Token reduction should not reintroduce escaped Unicode in tool content.
    """
    original_message = create_tool_message("tool_1", "TestTool", "original")
    chunks = [
        create_content_chunk("chunk_1", 'ページ名 "quoted"'),
        create_content_chunk("chunk_2", "مرحبا 😀"),
    ]

    result = loop_token_reducer._create_reduced_standard_sources_message(
        message=original_message,
        content_chunks=chunks,
        source_offset=2,
    )

    content = result.content
    assert isinstance(content, str)
    assert "ページ名" in content
    assert "مرحبا" in content
    assert "😀" in content
    assert "\\u30da" not in content

    content_dict = json.loads(content)
    assert content_dict[0]["source_number"] == 2
    assert content_dict[0]["content"] == 'ページ名 "quoted"'
    assert content_dict[1]["source_number"] == 3
    assert content_dict[1]["content"] == "مرحبا 😀"


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
def test_create_reduced_table_search_message__preserves_readable_unicode_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify reduced TableSearch messages keep non-ASCII content readable.
    Why this matters: TableSearch reduction serializes tool content separately from chunk history.
    """
    table_content = {
        "content": "ページ名 / マーケティングタグ / مرحبا 😀",
        "other_field": "value",
    }
    original_message = create_tool_message("tool_1", "TableSearch", table_content)
    chunk = create_content_chunk("chunk_1", "table result")

    result = loop_token_reducer._create_reduced_table_search_message(
        message=original_message,
        content_chunks=[chunk],
        source_offset=4,
    )

    content = result.content
    assert isinstance(content, str)
    assert "ページ名" in content
    assert "مرحبا" in content
    assert "😀" in content
    assert "\\u30da" not in content

    content_dict = json.loads(content)
    assert content_dict["source_number"] == 4
    assert content_dict["content"] == "ページ名 / マーケティングタグ / مرحبا 😀"


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


@pytest.mark.ai
def test_replace_user_message__appends_image_urls_as_content_parts__when_provided_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify _replace_user_message appends image data URLs as image_url parts
    with a text label before each image (so the LLM sees tool output images).
    Why this matters: MCP/internal tool responses with images must be visible to the LLM.
    """
    # Arrange
    history: list[LanguageModelMessage] = [
        LanguageModelSystemMessage(content="System prompt"),
        LanguageModelUserMessage(content="Original question"),
    ]
    original_user_message = "Original question"
    rendered_user_message = "Rendered question with context"
    image_data_from_tools: list[tuple[str, str]] = [
        ("data:image/png;base64,iVBORw0KGgo=", "call_abc"),
        ("data:image/jpeg;base64,/9j/4AAQ=", "call_xyz"),
    ]

    # Act
    result = loop_token_reducer._replace_user_message(
        history, original_user_message, rendered_user_message, image_data_from_tools
    )

    # Assert: one text part, then per (url, tool_call_id) a label (with ID) + image_url
    last_msg = result[-1]
    assert last_msg.role == LanguageModelMessageRole.USER
    assert isinstance(last_msg.content, list)
    assert len(last_msg.content) == 5  # text + (label + url) * 2
    assert last_msg.content[0] == {
        "type": "text",
        "text": "Rendered question with context",
    }
    assert last_msg.content[1]["type"] == "text"
    assert "tool call ID: call_abc" in last_msg.content[1]["text"]
    assert last_msg.content[2] == {
        "type": "image_url",
        "imageUrl": {"url": "data:image/png;base64,iVBORw0KGgo="},
    }
    assert last_msg.content[3]["type"] == "text"
    assert "tool call ID: call_xyz" in last_msg.content[3]["text"]
    assert last_msg.content[4] == {
        "type": "image_url",
        "imageUrl": {"url": "data:image/jpeg;base64,/9j/4AAQ="},
    }


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


@pytest.mark.ai
def test_limit_to_token_window__drops_whole_turn__when_turn_exceeds_budget_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Turn-based mode drops an entire turn when it doesn't fit.
    Why this matters: Partial turns would leave the window starting
    mid-sequence (e.g. ASSISTANT message before a USER), which confuses
    the LLM.
    """
    # Arrange – turn 1 is large, turn 2 fits on its own
    turn1: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="old question " * 50),
        LanguageModelAssistantMessage(content="old answer " * 50),
    ]
    turn2: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="recent question"),
        LanguageModelAssistantMessage(content="recent answer"),
    ]
    messages = turn1 + turn2

    # Find a budget that fits turn2 but not turn1+turn2
    turn2_tokens = loop_token_reducer._count_message_tokens(
        LanguageModelMessages(root=turn2)
    )
    token_limit = turn2_tokens + 5  # a few tokens of headroom, but not enough for turn1

    # Act
    result = loop_token_reducer._limit_to_token_window(
        messages, token_limit=token_limit
    )

    # Assert – only turn2 is included, never a partial turn1
    assert result == turn2


@pytest.mark.ai
def test_limit_to_token_window__includes_multiple_complete_turns__when_budget_allows_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Turn-based mode includes as many complete turns as the budget allows.
    Why this matters: History should be as rich as possible without splitting turns.
    """
    # Arrange
    turn1: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="q1"),
        LanguageModelAssistantMessage(content="a1"),
    ]
    turn2: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="q2"),
        LanguageModelAssistantMessage(content="a2"),
    ]
    turn3: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="q3"),
        LanguageModelAssistantMessage(content="a3"),
    ]
    messages = turn1 + turn2 + turn3

    # Act – generous budget that fits all three turns
    result = loop_token_reducer._limit_to_token_window(messages, token_limit=10_000)

    # Assert
    assert result == messages


@pytest.mark.ai
def test_limit_to_token_window__mid_turn_truncation__can_split_turn_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: allow_mid_turn_truncation=True uses per-message logic and may
    split a turn at the budget boundary.
    Why this matters: Some callers (e.g. those that follow up with
    ensure_last_message_is_user_message) want the raw per-message behaviour.
    """
    # Arrange – turn whose ASSISTANT message would push over the limit
    messages: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="question"),
        LanguageModelAssistantMessage(content="answer " * 200),
        LanguageModelUserMessage(content="follow-up"),
    ]
    user_only_tokens = loop_token_reducer._count_message_tokens(
        LanguageModelMessages(root=[messages[0], messages[2]])
    )
    # Budget fits the two USER messages but not the large ASSISTANT message
    token_limit = user_only_tokens + 5

    # Act
    result = loop_token_reducer._limit_to_token_window(
        messages, token_limit=token_limit, allow_mid_turn_truncation=True
    )

    # Assert – per-message mode kept the last USER message; the large
    # ASSISTANT message was dropped because it exceeded the budget
    assert result[-1].content == "follow-up"
    assert not any(m.content and "answer" in m.content for m in result)


@pytest.mark.ai
def test_limit_to_token_window__turn_based_default__preserves_tool_sequence_AI(
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Turn-based mode never splits an interleaved tool-call sequence.
    Why this matters: An assistant message referencing tool_call_ids without
    the matching tool messages causes LLM API rejections.
    """
    # Arrange – turn containing a tool-call sequence
    tool_turn: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="search for something"),
        LanguageModelAssistantMessage(
            content=None,
            tool_calls=[
                LanguageModelFunctionCall(
                    id="tc1",
                    function=LanguageModelFunction(name="search", arguments={}),
                )
            ],
        ),
        LanguageModelToolMessage(tool_call_id="tc1", content="results", name="search"),
        LanguageModelAssistantMessage(content="Here is what I found."),
    ]
    follow_up_turn: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="thanks"),
    ]
    messages = tool_turn + follow_up_turn

    # Budget fits only the follow-up turn
    follow_up_tokens = loop_token_reducer._count_message_tokens(
        LanguageModelMessages(root=follow_up_turn)
    )
    token_limit = follow_up_tokens + 5

    # Act
    result = loop_token_reducer._limit_to_token_window(
        messages, token_limit=token_limit
    )

    # Assert – tool_turn is dropped as a whole unit, not partially included
    assert result == follow_up_turn


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
        loop_token_reducer._reduce_message_length_by_reducing_tool_responses_content(
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
    Purpose: Verify _get_encoder returns correct encoder callable.
    Why this matters: Correct encoder is essential for accurate token counting.
    """
    # Arrange & Act
    encoder = loop_token_reducer._get_encoder(language_model_info)

    # Assert
    assert encoder is not None
    assert callable(encoder)
    # Verify encoder works by encoding a simple string
    tokens = encoder("Hello world")
    assert len(tokens) > 0


@pytest.mark.ai
def test_get_encoder__uses_model_get_encoder_AI(
    loop_token_reducer: LoopTokenReducer,
    language_model_info: LanguageModelInfo,
) -> None:
    """
    Purpose: Verify _get_encoder uses language_model.get_encoder().
    Why this matters: Ensures encoder is retrieved from model_info correctly.
    """
    # Arrange & Act
    encoder = loop_token_reducer._get_encoder(language_model_info)

    # Assert
    assert encoder is not None
    assert callable(encoder)
    tokens = encoder("Test")
    assert len(tokens) > 0


# Integration-style Tests (still unit tests but test larger flows)
@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.history_manager.loop_token_reducer.get_full_history_with_contents_async"
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


@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.history_manager.loop_token_reducer.get_full_history_with_contents_async"
)
@patch.object(LoopTokenReducer, "_count_message_tokens")
async def test_get_history_for_model_call__appends_image_urls_to_user_message__when_provided_AI(
    mock_count_tokens: "Mock",
    mock_get_history: "Mock",
    loop_token_reducer: LoopTokenReducer,
) -> None:
    """
    Purpose: Verify get_history_for_model_call includes image_url parts when image_data_urls_from_tools provided.
    Why this matters: Tool-returned images must appear in the user message for the LLM.
    """
    # Arrange
    mock_get_history.return_value = LanguageModelMessages(
        root=[LanguageModelUserMessage(content="Original question")]
    )
    mock_count_tokens.return_value = 100

    async def mock_remove_from_text(text: str) -> str:
        return text

    # Act
    result = await loop_token_reducer.get_history_for_model_call(
        original_user_message="Original question",
        rendered_user_message_string="Rendered question",
        rendered_system_message_string="System prompt",
        loop_history=[],
        remove_from_text=mock_remove_from_text,
        image_data_urls_from_tools=[
            ("data:image/png;base64,iVBORw0KGgo=", "call_123"),
        ],
    )

    # Assert
    user_messages = [m for m in result.root if m.role == LanguageModelMessageRole.USER]
    assert user_messages
    last_user = user_messages[-1]
    assert isinstance(last_user.content, list)
    image_parts = [
        p
        for p in last_user.content
        if isinstance(p, dict) and p.get("type") == "image_url"
    ]
    assert image_parts
    assert (
        image_parts[0].get("imageUrl", {}).get("url")
        == "data:image/png;base64,iVBORw0KGgo="
    )


# Feature flag path tests
@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.history_manager.loop_token_reducer.get_full_history_with_contents_async"
)
@patch.object(LoopTokenReducer, "_count_message_tokens")
async def test_get_history_from_db__calls_without_tool_calls__when_persistence_disabled_AI(
    mock_count_tokens: "Mock",
    mock_get_history: "Mock",
    mock_logger: Logger,
    test_event: ChatEvent,
    mock_reference_manager: ReferenceManager,
    language_model_info: LanguageModelInfo,
) -> None:
    """
    Purpose: Verify get_history_from_db calls get_full_history_with_contents_async (not the tool-call
        variant) when enable_tool_call_persistence=False.
    Why this matters: With the flag off, we must avoid the DB round-trip that loads ToolCall
        records, keeping the code path identical to before the feature was introduced.
    Setup summary: LoopTokenReducer constructed with enable_tool_call_persistence=False;
        assert get_full_history_with_contents_async is called once.
    """
    reducer = LoopTokenReducer(
        logger=mock_logger,
        event=test_event,
        max_history_tokens=4000,
        reference_manager=mock_reference_manager,
        language_model=language_model_info,
        enable_tool_call_persistence=False,
    )
    mock_get_history.return_value = LanguageModelMessages(
        root=[LanguageModelUserMessage(content="hello")]
    )
    mock_count_tokens.return_value = 100

    async def noop(text: str) -> str:
        return text

    await reducer.get_history_for_model_call(
        original_user_message="hello",
        rendered_user_message_string="hello",
        rendered_system_message_string="system",
        loop_history=[],
        remove_from_text=noop,
    )

    mock_get_history.assert_called_once()
    assert (
        mock_get_history.call_args.kwargs["file_content_serializer"]
        is reducer._file_content_serializer
    )


@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.history_manager.loop_token_reducer.get_full_history_with_contents_and_tool_calls_async"
)
@patch.object(LoopTokenReducer, "_count_message_tokens")
async def test_get_history_from_db__calls_with_tool_calls__when_persistence_enabled_AI(
    mock_count_tokens: "Mock",
    mock_get_history: "Mock",
    mock_logger: Logger,
    test_event: ChatEvent,
    mock_reference_manager: ReferenceManager,
    language_model_info: LanguageModelInfo,
) -> None:
    """
    Purpose: Verify get_history_from_db calls get_full_history_with_contents_and_tool_calls_async
        when enable_tool_call_persistence=True.
    Why this matters: With the flag on, prior-turn tool call records must be loaded from the
        DB so that source numbering can continue from where the last turn left off.
    Setup summary: LoopTokenReducer constructed with enable_tool_call_persistence=True;
        assert get_full_history_with_contents_and_tool_calls_async is called and max_db_source_number
        is populated from its return value.
    """
    reducer = LoopTokenReducer(
        logger=mock_logger,
        event=test_event,
        max_history_tokens=4000,
        reference_manager=mock_reference_manager,
        language_model=language_model_info,
        enable_tool_call_persistence=True,
    )
    mock_get_history.return_value = (
        LanguageModelMessages(root=[LanguageModelUserMessage(content="hello")]),
        5,
        {},
    )
    mock_count_tokens.return_value = 100

    async def noop(text: str) -> str:
        return text

    await reducer.get_history_for_model_call(
        original_user_message="hello",
        rendered_user_message_string="hello",
        rendered_system_message_string="system",
        loop_history=[],
        remove_from_text=noop,
    )

    mock_get_history.assert_called_once()
    assert reducer.max_db_source_number == 5


# UN-23154 regression
@pytest.mark.ai
@patch(
    "unique_toolkit.agentic.history_manager.loop_token_reducer.get_full_history_with_contents_and_tool_calls_async"
)
async def test_get_history_from_db__preserves_oldest_turn__when_recent_tool_outputs_are_huge_AI(
    mock_get_history: "Mock",
    mock_logger: Logger,
    test_event: ChatEvent,
    mock_reference_manager: ReferenceManager,
    language_model_info: LanguageModelInfo,
) -> None:
    """UN-23154: a tiny oldest turn must survive when recent turns carry huge
    persisted tool outputs.

    With tool-call persistence the DB history includes every prior turn's full
    tool output. The only lever applied to that history today is dropping whole
    turns (``_limit_to_token_window``), and the content-reduction levers
    (source dropping / plain-text truncation) are applied only to the current
    loop history. So a couple of huge recent tool turns exhaust the history
    budget and the oldest — often tiny and semantically important — turn is
    evicted wholesale instead of shrinking the large recent tool outputs. This
    is the wholesale-clearing symptom in the ticket. The fix must shrink older
    tool-response content before dropping whole turns so turn 1 survives.
    """
    # Arrange – turn 1 is tiny (the recall anchor); turns 2-4 carry huge
    # chunk-less plain-text tool outputs.
    tiny_turn: list[LanguageModelMessage] = [
        LanguageModelUserMessage(content="What EUR/USD rate did you report first?"),
        LanguageModelAssistantMessage(content="EUR/USD was 1.1427."),
    ]

    def big_tool_turn(question: str, tool_call_id: str) -> list[LanguageModelMessage]:
        return [
            LanguageModelUserMessage(content=question),
            LanguageModelAssistantMessage(
                content=None,
                tool_calls=[
                    LanguageModelFunctionCall(
                        id=tool_call_id,
                        function=LanguageModelFunction(
                            name="InternalSearch", arguments={}
                        ),
                    )
                ],
            ),
            LanguageModelToolMessage(
                tool_call_id=tool_call_id,
                name="InternalSearch",
                content="HUGE RESULT " * 4000,  # ~48k chars, chunk-less plain text
            ),
            LanguageModelAssistantMessage(content="Here is the answer."),
        ]

    turn2 = big_tool_turn("internal search 2", "tc2")
    turn3 = big_tool_turn("internal search 3", "tc3")
    turn4 = big_tool_turn("internal search 4", "tc4")
    full = tiny_turn + turn2 + turn3 + turn4

    reducer = LoopTokenReducer(
        logger=mock_logger,
        event=test_event,
        max_history_tokens=1,  # overridden below once we can measure turns
        reference_manager=mock_reference_manager,
        language_model=language_model_info,
        enable_tool_call_persistence=True,
    )

    def turn_tokens(turn: list[LanguageModelMessage]) -> int:
        return reducer._count_message_tokens(LanguageModelMessages(root=turn))

    # Budget holds the two newest huge turns plus the tiny oldest turn, but not a
    # third huge turn at full size. Greedy whole-turn dropping therefore keeps
    # only turns 3 & 4 and evicts turns 1 & 2 — losing the anchor. If older tool
    # outputs are shrunk instead, all four turns fit and turn 1 survives.
    reducer._max_history_tokens = (
        turn_tokens(tiny_turn) + turn_tokens(turn3) + turn_tokens(turn4) + 20
    )

    async def fake_history(**_kwargs: object):
        return (LanguageModelMessages(root=list(full)), 0, {})

    mock_get_history.side_effect = fake_history

    # Act
    result = await reducer.get_history_from_db()

    # Assert – the oldest turn's user message must still be present.
    result_text = " ".join(m.content for m in result if isinstance(m.content, str))
    assert "What EUR/USD rate did you report first?" in result_text, (
        "UN-23154: oldest turn was evicted wholesale instead of shrinking the "
        "large recent tool outputs to make room."
    )


# ---------------------------------------------------------------------------
# get_selected_uploaded_content_ids (shared utility)
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_get_selected_uploaded_content_ids_ff_disabled(test_event):
    """When the feature flag is disabled, should return None."""
    from unique_toolkit.agentic.history_manager.utils import (
        get_selected_uploaded_content_ids,
    )

    with patch("unique_toolkit.agentic.history_manager.utils.feature_flags") as ff:
        ff.enable_selected_uploaded_files_un_18215.is_enabled.return_value = False
        result = get_selected_uploaded_content_ids(test_event)
    assert result is None


@pytest.mark.ai
def test_get_selected_uploaded_content_ids_ff_enabled_with_selection(test_event):
    """When FF is enabled and files are selected, should return the selected IDs."""
    from unique_toolkit.agentic.history_manager.utils import (
        get_selected_uploaded_content_ids,
    )

    additional = MagicMock()
    additional.selected_uploaded_file_ids = ["file_1", "file_2"]
    test_event.payload.additional_parameters = additional

    with patch("unique_toolkit.agentic.history_manager.utils.feature_flags") as ff:
        ff.enable_selected_uploaded_files_un_18215.is_enabled.return_value = True
        result = get_selected_uploaded_content_ids(test_event)
    assert result == {"file_1", "file_2"}


@pytest.mark.ai
def test_get_selected_uploaded_content_ids_ff_enabled_no_additional_params(
    test_event,
):
    """When FF is enabled but additional_parameters is None, should return None."""
    from unique_toolkit.agentic.history_manager.utils import (
        get_selected_uploaded_content_ids,
    )

    test_event.payload.additional_parameters = None

    with patch("unique_toolkit.agentic.history_manager.utils.feature_flags") as ff:
        ff.enable_selected_uploaded_files_un_18215.is_enabled.return_value = True
        result = get_selected_uploaded_content_ids(test_event)
    assert result is None


@pytest.mark.ai
def test_get_selected_uploaded_content_ids_ff_enabled_empty_selection(test_event):
    """When FF is enabled but no files selected, should return empty set."""
    from unique_toolkit.agentic.history_manager.utils import (
        get_selected_uploaded_content_ids,
    )

    additional = MagicMock()
    additional.selected_uploaded_file_ids = []
    test_event.payload.additional_parameters = additional

    with patch("unique_toolkit.agentic.history_manager.utils.feature_flags") as ff:
        ff.enable_selected_uploaded_files_un_18215.is_enabled.return_value = True
        result = get_selected_uploaded_content_ids(test_event)
    assert result == set()
