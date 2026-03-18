"""Tests for hallucination evaluation utils."""

from typing import List, Optional

import pytest

from unique_toolkit.agentic.evaluation.hallucination.constants import (
    HallucinationConfig,
    SourceSelectionMode,
)
from unique_toolkit.agentic.evaluation.hallucination.utils import (
    _compose_msgs,
    _default_source_selection_mode,
    _from_order_source_selection_mode,
    _from_original_response_source_selection_mode,
    _get_msgs,
    context_text_from_stream_response,
)
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricInput
from unique_toolkit.content import ContentReference
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
)


@pytest.fixture
def sample_chunks() -> List[ContentChunk]:
    """Create sample content chunks for testing."""
    return [
        ContentChunk(
            id="cont_123",
            chunk_id="chunk_001",
            text="First chunk text",
            order=0,
        ),
        ContentChunk(
            id="cont_123",
            chunk_id="chunk_002",
            text="Second chunk text",
            order=1,
        ),
        ContentChunk(
            id="cont_456",
            chunk_id="chunk_003",
            text="Third chunk text",
            order=0,
        ),
        ContentChunk(
            id="cont_456",
            chunk_id="chunk_004",
            text="Fourth chunk text",
            order=1,
        ),
    ]


@pytest.fixture
def sample_references() -> List[ContentReference]:
    """Create sample content references for testing."""
    return [
        ContentReference(
            name="Reference 1",
            sequence_number=1,
            source="test_source",
            source_id="cont_123_chunk_001",
            url="http://example.com/1",
            original_index=[0],
        ),
        ContentReference(
            name="Reference 2",
            sequence_number=2,
            source="test_source",
            source_id="cont_456_chunk_003",
            url="http://example.com/2",
            original_index=[2],
        ),
    ]


@pytest.fixture
def hallucination_config() -> HallucinationConfig:
    """Create a hallucination config for testing."""
    return HallucinationConfig(enabled=True)


@pytest.fixture
def evaluation_input() -> EvaluationMetricInput:
    """Create an evaluation input for testing."""
    return EvaluationMetricInput(
        input_text="Test question",
        context_texts=["Context 1", "Context 2"],
        output_text="Test output",
    )


@pytest.mark.ai
def test_default_source_selection_mode__selects_chunks__by_source_id_match(
    sample_references: List[ContentReference],
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that chunks are selected by matching source_id from references.
    Why this matters: FROM_IDS mode is the most precise chunk selection method.
    Setup summary: Provide references with source IDs, assert matching chunks selected.
    """
    # Arrange - Fixtures provide data

    # Act
    result: List[ContentChunk] = _default_source_selection_mode(
        sample_references, sample_chunks
    )

    # Assert
    assert len(result) == 2
    assert result[0].chunk_id == "chunk_001"
    assert result[1].chunk_id == "chunk_003"


@pytest.mark.ai
def test_default_source_selection_mode__returns_empty_list__when_no_matches_found(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that empty list is returned when no references match chunks.
    Why this matters: Graceful handling of missing references is critical.
    Setup summary: Provide non-matching reference, assert empty result.
    """
    # Arrange
    references: List[ContentReference] = [
        ContentReference(
            name="No Match",
            sequence_number=1,
            source="test",
            source_id="nonexistent_id",
            url="http://example.com",
            original_index=[0],
        )
    ]

    # Act
    result: List[ContentChunk] = _default_source_selection_mode(
        references, sample_chunks
    )

    # Assert
    assert len(result) == 0


@pytest.mark.ai
def test_default_source_selection_mode__returns_empty_list__with_empty_references(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that empty list is returned when references list is empty.
    Why this matters: Handles edge case of no references gracefully.
    Setup summary: Provide empty references list, assert empty result.
    """
    # Arrange
    references: List[ContentReference] = []

    # Act
    result: List[ContentChunk] = _default_source_selection_mode(
        references, sample_chunks
    )

    # Assert
    assert len(result) == 0


@pytest.mark.ai
def test_default_source_selection_mode__returns_empty_list__with_empty_chunks(
    sample_references: List[ContentReference],
) -> None:
    """
    Purpose: Verify that empty list is returned when chunks list is empty.
    Why this matters: Handles edge case of no available chunks gracefully.
    Setup summary: Provide empty chunks list, assert empty result.
    """
    # Arrange
    chunks: List[ContentChunk] = []

    # Act
    result: List[ContentChunk] = _default_source_selection_mode(
        sample_references, chunks
    )

    # Assert
    assert len(result) == 0


@pytest.mark.ai
def test_default_source_selection_mode__builds_chunk_id_correctly__for_matching(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that chunk IDs are built correctly using id_chunkId format.
    Why this matters: Correct ID construction is critical for chunk matching.
    Setup summary: Provide reference with specific ID format, assert correct chunk found.
    """
    # Arrange
    references: List[ContentReference] = [
        ContentReference(
            name="Ref",
            sequence_number=1,
            source="test",
            source_id="cont_123_chunk_001",
            url="http://example.com",
            original_index=[0],
        )
    ]

    # Act
    result: List[ContentChunk] = _default_source_selection_mode(
        references, sample_chunks
    )

    # Assert
    assert len(result) == 1
    assert result[0].id == "cont_123"
    assert result[0].chunk_id == "chunk_001"


@pytest.mark.ai
def test_from_order_source_selection_mode__selects_chunks__by_original_index_order(
    sample_references: List[ContentReference],
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that chunks are selected by original_index values from references.
    Why this matters: FROM_ORDER mode enables position-based chunk selection.
    Setup summary: Provide references with original indices, assert chunks at those positions.
    """
    # Arrange - Fixtures provide data

    # Act
    result: List[ContentChunk] = _from_order_source_selection_mode(
        sample_references, sample_chunks
    )

    # Assert
    assert len(result) == 2
    assert result[0] == sample_chunks[0]  # original_index [0]
    assert result[1] == sample_chunks[2]  # original_index [2]


@pytest.mark.ai
def test_from_order_source_selection_mode__handles_multiple_indices__in_single_reference(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify handling of references with multiple original indices.
    Why this matters: Single reference may cite multiple chunks.
    Setup summary: Provide reference with multiple indices, assert all chunks selected.
    """
    # Arrange
    references: List[ContentReference] = [
        ContentReference(
            name="Multi",
            sequence_number=1,
            source="test",
            source_id="test_id",
            url="http://example.com",
            original_index=[0, 2, 3],
        )
    ]

    # Act
    result: List[ContentChunk] = _from_order_source_selection_mode(
        references, sample_chunks
    )

    # Assert
    assert len(result) == 3
    assert result[0] == sample_chunks[0]
    assert result[1] == sample_chunks[2]
    assert result[2] == sample_chunks[3]


@pytest.mark.ai
def test_from_order_source_selection_mode__removes_duplicate_indices__while_preserving_order(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that duplicate indices across references are deduplicated.
    Why this matters: Prevents duplicate chunks in context while maintaining order.
    Setup summary: Provide overlapping indices, assert deduplicated result.
    """
    # Arrange
    references: List[ContentReference] = [
        ContentReference(
            name="Ref1",
            sequence_number=1,
            source="test",
            source_id="id1",
            url="http://example.com",
            original_index=[0, 1],
        ),
        ContentReference(
            name="Ref2",
            sequence_number=2,
            source="test",
            source_id="id2",
            url="http://example.com",
            original_index=[1, 2],  # 1 is duplicate
        ),
    ]

    # Act
    result: List[ContentChunk] = _from_order_source_selection_mode(
        references, sample_chunks
    )

    # Assert
    assert len(result) == 3  # 0, 1, 2 (no duplicate 1)
    assert result[0] == sample_chunks[0]
    assert result[1] == sample_chunks[1]
    assert result[2] == sample_chunks[2]


@pytest.mark.ai
def test_from_order_source_selection_mode__returns_empty_list__with_empty_references(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that empty list is returned when references list is empty.
    Why this matters: Handles edge case gracefully without errors.
    Setup summary: Provide empty references, assert empty result.
    """
    # Arrange
    references: List[ContentReference] = []

    # Act
    result: List[ContentChunk] = _from_order_source_selection_mode(
        references, sample_chunks
    )

    # Assert
    assert len(result) == 0


@pytest.mark.ai
def test_from_order_source_selection_mode__preserves_order__from_reference_appearance(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that chunk order matches the order indices appear in references.
    Why this matters: Order preservation maintains citation flow from original response.
    Setup summary: Provide indices in specific order, assert result matches that order.
    """
    # Arrange
    references: List[ContentReference] = [
        ContentReference(
            name="Ref",
            sequence_number=1,
            source="test",
            source_id="id",
            url="http://example.com",
            original_index=[3, 1, 0],  # Specific order
        )
    ]

    # Act
    result: List[ContentChunk] = _from_order_source_selection_mode(
        references, sample_chunks
    )

    # Assert
    assert len(result) == 3
    assert result[0] == sample_chunks[3]
    assert result[1] == sample_chunks[1]
    assert result[2] == sample_chunks[0]


@pytest.mark.ai
def test_from_original_response_source_selection_mode__extracts_source_numbers__from_text(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify extraction of source numbers from text using regex pattern.
    Why this matters: Enables detection of actually cited sources in generated text.
    Setup summary: Provide text with source citations, assert correct chunks extracted.
    """
    # Arrange
    original_text: str = "Based on [source0] and [source2], we can conclude..."
    pattern: str = r"[\[<]?source(\d+)[>\]]?"

    # Act
    result: List[ContentChunk] = _from_original_response_source_selection_mode(
        original_text, sample_chunks, pattern
    )

    # Assert
    assert len(result) == 2
    assert result[0] == sample_chunks[0]
    assert result[1] == sample_chunks[2]


@pytest.mark.ai
def test_from_original_response_source_selection_mode__handles_different_reference_formats(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify extraction works with multiple reference format variations.
    Why this matters: Different systems may use different citation formats.
    Setup summary: Provide text with mixed citation formats, assert all extracted.
    """
    # Arrange
    original_text: str = "From <source0> and source1 and [source3]"
    pattern: str = r"[\[<]?source(\d+)[>\]]?"

    # Act
    result: List[ContentChunk] = _from_original_response_source_selection_mode(
        original_text, sample_chunks, pattern
    )

    # Assert
    assert len(result) == 3
    assert result[0] == sample_chunks[0]
    assert result[1] == sample_chunks[1]
    assert result[2] == sample_chunks[3]


@pytest.mark.ai
def test_from_original_response_source_selection_mode__removes_duplicate_references__while_preserving_order(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that duplicate source citations are deduplicated.
    Why this matters: Prevents duplicate chunks in evaluation context.
    Setup summary: Provide text with repeated citations, assert deduplicated result.
    """
    # Arrange
    original_text: str = "[source0] [source1] [source0] [source2]"
    pattern: str = r"[\[<]?source(\d+)[>\]]?"

    # Act
    result: List[ContentChunk] = _from_original_response_source_selection_mode(
        original_text, sample_chunks, pattern
    )

    # Assert
    assert len(result) == 3  # 0, 1, 2 (no duplicate 0)
    assert result[0] == sample_chunks[0]
    assert result[1] == sample_chunks[1]
    assert result[2] == sample_chunks[2]


@pytest.mark.ai
def test_from_original_response_source_selection_mode__raises_value_error__when_original_text_is_none(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that ValueError is raised when original_text is None.
    Why this matters: This mode requires original text to extract citations.
    Setup summary: Call with None text, assert ValueError with descriptive message.
    """
    # Arrange
    original_text: Optional[str] = None
    pattern: str = r"[\[<]?source(\d+)[>\]]?"

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        _from_original_response_source_selection_mode(
            original_text,
            sample_chunks,
            pattern,  # type: ignore
        )

    assert "original_text is required" in str(exc_info.value)


@pytest.mark.ai
def test_from_original_response_source_selection_mode__filters_out_of_bounds_indices(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that source indices beyond chunk list length are filtered out.
    Why this matters: Prevents index errors and gracefully handles invalid references.
    Setup summary: Provide text with out-of-bounds index, assert it's filtered.
    """
    # Arrange
    original_text: str = "[source0] [source10] [source2]"  # source10 is out of bounds
    pattern: str = r"[\[<]?source(\d+)[>\]]?"

    # Act
    result: List[ContentChunk] = _from_original_response_source_selection_mode(
        original_text, sample_chunks, pattern
    )

    # Assert
    assert len(result) == 2
    assert result[0] == sample_chunks[0]
    assert result[1] == sample_chunks[2]


@pytest.mark.ai
def test_from_original_response_source_selection_mode__returns_empty_list__when_no_references_found(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that empty list is returned when no citations found in text.
    Why this matters: Handles case of text without source citations gracefully.
    Setup summary: Provide text with no citations, assert empty result.
    """
    # Arrange
    original_text: str = "No references in this text"
    pattern: str = r"[\[<]?source(\d+)[>\]]?"

    # Act
    result: List[ContentChunk] = _from_original_response_source_selection_mode(
        original_text, sample_chunks, pattern
    )

    # Assert
    assert len(result) == 0


@pytest.mark.ai
def test_from_original_response_source_selection_mode__works_with_custom_regex_pattern(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that custom regex patterns can be used for extraction.
    Why this matters: Enables support for organization-specific citation formats.
    Setup summary: Provide custom pattern and matching text, assert extraction works.
    """
    # Arrange
    original_text: str = "See ref:0 and ref:2 for details"
    pattern: str = r"ref:(\d+)"

    # Act
    result: List[ContentChunk] = _from_original_response_source_selection_mode(
        original_text, sample_chunks, pattern
    )

    # Assert
    assert len(result) == 2
    assert result[0] == sample_chunks[0]
    assert result[1] == sample_chunks[2]


@pytest.mark.ai
def test_from_original_response_source_selection_mode__preserves_order__from_text_appearance(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that chunk order matches citation order in original text.
    Why this matters: Order preservation maintains logical flow of cited sources.
    Setup summary: Provide text with specific citation order, assert result matches.
    """
    # Arrange
    original_text: str = "[source3] [source1] [source0]"
    pattern: str = r"[\[<]?source(\d+)[>\]]?"

    # Act
    result: List[ContentChunk] = _from_original_response_source_selection_mode(
        original_text, sample_chunks, pattern
    )

    # Assert
    assert len(result) == 3
    assert result[0] == sample_chunks[3]
    assert result[1] == sample_chunks[1]
    assert result[2] == sample_chunks[0]


@pytest.mark.ai
def test_context_text_from_stream_response__extracts_context__using_from_ids_mode(
    sample_chunks: List[ContentChunk],
    sample_references: List[ContentReference],
) -> None:
    """
    Purpose: Verify context extraction using FROM_IDS source selection mode.
    Why this matters: FROM_IDS is most accurate mode for known reference IDs.
    Setup summary: Create response with references, use FROM_IDS mode, assert correct texts.
    """
    # Arrange
    response: LanguageModelStreamResponse = LanguageModelStreamResponse(
        message=LanguageModelStreamResponseMessage(
            id="msg_1",
            previous_message_id=None,
            role=LanguageModelMessageRole.ASSISTANT,
            text="Test",
            references=sample_references,
        )
    )

    # Act
    result: List[str] = context_text_from_stream_response(
        response, sample_chunks, SourceSelectionMode.FROM_IDS
    )

    # Assert
    assert len(result) == 2
    assert result[0] == "First chunk text"
    assert result[1] == "Third chunk text"


@pytest.mark.ai
def test_context_text_from_stream_response__extracts_context__using_from_order_mode(
    sample_chunks: List[ContentChunk],
    sample_references: List[ContentReference],
) -> None:
    """
    Purpose: Verify context extraction using FROM_ORDER source selection mode.
    Why this matters: FROM_ORDER enables index-based chunk selection.
    Setup summary: Create response with references, use FROM_ORDER mode, assert strings returned.
    """
    # Arrange
    response: LanguageModelStreamResponse = LanguageModelStreamResponse(
        message=LanguageModelStreamResponseMessage(
            id="msg_1",
            previous_message_id=None,
            role=LanguageModelMessageRole.ASSISTANT,
            text="Test",
            references=sample_references,
        )
    )

    # Act
    result: List[str] = context_text_from_stream_response(
        response, sample_chunks, SourceSelectionMode.FROM_ORDER
    )

    # Assert
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], str)


@pytest.mark.ai
def test_context_text_from_stream_response__extracts_context__using_from_original_response_mode(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify context extraction using FROM_ORIGINAL_RESPONSE mode.
    Why this matters: Extracts only sources actually cited in generated text.
    Setup summary: Create response with original_text citations, assert extraction works.
    """
    # Arrange
    references: List[ContentReference] = [
        ContentReference(
            name="Ref",
            sequence_number=1,
            source="test",
            source_id="id",
            url="http://example.com",
            original_index=[0],
        )
    ]
    response: LanguageModelStreamResponse = LanguageModelStreamResponse(
        message=LanguageModelStreamResponseMessage(
            id="msg_1",
            previous_message_id=None,
            role=LanguageModelMessageRole.ASSISTANT,
            text="Test",
            original_text="Based on [source0] and [source2]",
            references=references,
        )
    )
    pattern: str = r"[\[<]?source(\d+)[>\]]?"

    # Act
    result: List[str] = context_text_from_stream_response(
        response,
        sample_chunks,
        SourceSelectionMode.FROM_ORIGINAL_RESPONSE,
        pattern,
    )

    # Assert
    assert len(result) == 2
    assert result[0] == "First chunk text"
    assert result[1] == "Third chunk text"


@pytest.mark.ai
def test_context_text_from_stream_response__falls_back_to_default__with_invalid_mode(
    sample_chunks: List[ContentChunk],
    sample_references: List[ContentReference],
) -> None:
    """
    Purpose: Verify that invalid mode falls back to FROM_IDS mode gracefully.
    Why this matters: Ensures robustness against configuration errors.
    Setup summary: Use invalid mode string, assert fallback returns results.
    """
    # Arrange
    response: LanguageModelStreamResponse = LanguageModelStreamResponse(
        message=LanguageModelStreamResponseMessage(
            id="msg_1",
            previous_message_id=None,
            role=LanguageModelMessageRole.ASSISTANT,
            text="Test",
            references=sample_references,
        )
    )

    # Act
    result: List[str] = context_text_from_stream_response(
        response,
        sample_chunks,
        "INVALID_MODE",  # type: ignore
    )

    # Assert
    assert len(result) == 2


@pytest.mark.ai
def test_context_text_from_stream_response__falls_back_to_default__on_extraction_error(
    sample_chunks: List[ContentChunk],
) -> None:
    """
    Purpose: Verify that extraction errors trigger fallback to default mode.
    Why this matters: Ensures evaluation continues even with malformed data.
    Setup summary: Create scenario that causes error, assert fallback succeeds.
    """
    # Arrange
    references: List[ContentReference] = [
        ContentReference(
            name="Ref",
            sequence_number=1,
            source="test",
            source_id="cont_123_chunk_001",
            url="http://example.com",
            original_index=[0],
        )
    ]
    response: LanguageModelStreamResponse = LanguageModelStreamResponse(
        message=LanguageModelStreamResponseMessage(
            id="msg_1",
            previous_message_id=None,
            role=LanguageModelMessageRole.ASSISTANT,
            text="Test",
            original_text=None,  # Will cause error in FROM_ORIGINAL_RESPONSE
            references=references,
        )
    )

    # Act
    result: List[str] = context_text_from_stream_response(
        response, sample_chunks, SourceSelectionMode.FROM_ORIGINAL_RESPONSE
    )

    # Assert
    assert len(result) == 1
    assert result[0] == "First chunk text"


@pytest.mark.ai
def test_context_text_from_stream_response__returns_text_strings__not_chunk_objects(
    sample_chunks: List[ContentChunk],
    sample_references: List[ContentReference],
) -> None:
    """
    Purpose: Verify that function returns list of text strings, not ContentChunk objects.
    Why this matters: Evaluation expects string context, not chunk objects.
    Setup summary: Call function, assert all results are strings not ContentChunk instances.
    """
    # Arrange
    response: LanguageModelStreamResponse = LanguageModelStreamResponse(
        message=LanguageModelStreamResponseMessage(
            id="msg_1",
            previous_message_id=None,
            role=LanguageModelMessageRole.ASSISTANT,
            text="Test",
            references=sample_references,
        )
    )

    # Act
    result: List[str] = context_text_from_stream_response(
        response, sample_chunks, SourceSelectionMode.FROM_IDS
    )

    # Assert
    assert all(isinstance(text, str) for text in result)
    assert not any(isinstance(text, ContentChunk) for text in result)


@pytest.mark.ai
def test_get_msgs__composes_messages__with_context_and_history(
    hallucination_config: HallucinationConfig,
) -> None:
    """
    Purpose: Verify message composition with both context and history provided.
    Why this matters: Full context enables accurate hallucination detection.
    Setup summary: Create input with all fields, assert message structure.
    """
    # Arrange
    input_data: EvaluationMetricInput = EvaluationMetricInput(
        input_text="Question",
        context_texts=["Context 1"],
        history_messages=[],
        output_text="Output",
    )

    # Act
    result: LanguageModelMessages = _get_msgs(input_data, hallucination_config)

    # Assert
    assert isinstance(result, LanguageModelMessages)
    assert len(result.root) == 2


@pytest.mark.ai
def test_get_msgs__composes_messages__without_context_or_history(
    hallucination_config: HallucinationConfig,
) -> None:
    """
    Purpose: Verify message composition works without context or history.
    Why this matters: Hallucination can be detected even without grounding context.
    Setup summary: Create input with only input/output, assert message structure.
    """
    # Arrange
    input_data: EvaluationMetricInput = EvaluationMetricInput(
        input_text="Question",
        output_text="Output",
    )

    # Act
    result: LanguageModelMessages = _get_msgs(input_data, hallucination_config)

    # Assert
    assert isinstance(result, LanguageModelMessages)
    assert len(result.root) == 2


@pytest.mark.ai
def test_get_msgs__composes_messages__with_context_texts_only(
    hallucination_config: HallucinationConfig,
) -> None:
    """
    Purpose: Verify message composition with context texts but no history.
    Why this matters: Common scenario for single-turn evaluations.
    Setup summary: Create input with context but no history, assert message structure.
    """
    # Arrange
    input_data: EvaluationMetricInput = EvaluationMetricInput(
        input_text="Question",
        context_texts=["Context 1", "Context 2"],
        output_text="Output",
    )

    # Act
    result: LanguageModelMessages = _get_msgs(input_data, hallucination_config)

    # Assert
    assert isinstance(result, LanguageModelMessages)
    assert len(result.root) == 2


@pytest.mark.ai
def test_compose_msgs__creates_valid_messages__with_context(
    hallucination_config: HallucinationConfig,
) -> None:
    """
    Purpose: Verify that messages are composed correctly when context is available.
    Why this matters: Context affects prompt template rendering.
    Setup summary: Call with has_context=True, assert message structure.
    """
    # Arrange
    input_data: EvaluationMetricInput = EvaluationMetricInput(
        input_text="Question",
        context_texts=["Context 1"],
        output_text="Output",
    )

    # Act
    result: LanguageModelMessages = _compose_msgs(
        input_data, hallucination_config, has_context=True
    )

    # Assert
    assert isinstance(result, LanguageModelMessages)
    assert len(result.root) == 2
    assert result.root[0].role == "system"
    assert result.root[1].role == "user"


@pytest.mark.ai
def test_compose_msgs__creates_valid_messages__without_context(
    hallucination_config: HallucinationConfig,
) -> None:
    """
    Purpose: Verify that messages are composed correctly when context is absent.
    Why this matters: No-context mode uses different prompt template.
    Setup summary: Call with has_context=False, assert message structure.
    """
    # Arrange
    input_data: EvaluationMetricInput = EvaluationMetricInput(
        input_text="Question",
        output_text="Output",
    )

    # Act
    result: LanguageModelMessages = _compose_msgs(
        input_data, hallucination_config, has_context=False
    )

    # Assert
    assert isinstance(result, LanguageModelMessages)
    assert len(result.root) == 2


@pytest.mark.ai
def test_compose_msgs__uses_different_system_prompts__based_on_context_flag(
    hallucination_config: HallucinationConfig,
) -> None:
    """
    Purpose: Verify that system message content differs based on has_context flag.
    Why this matters: Different prompts needed for grounded vs ungrounded evaluation.
    Setup summary: Call with both flags, assert system prompts differ.
    """
    # Arrange
    input_data: EvaluationMetricInput = EvaluationMetricInput(
        input_text="Question",
        output_text="Output",
    )

    # Act
    result_with_context: LanguageModelMessages = _compose_msgs(
        input_data, hallucination_config, has_context=True
    )
    result_without_context: LanguageModelMessages = _compose_msgs(
        input_data, hallucination_config, has_context=False
    )

    # Assert
    assert result_with_context.root[0].content != result_without_context.root[0].content


@pytest.mark.ai
def test_compose_msgs__includes_input_text__in_user_message(
    hallucination_config: HallucinationConfig,
) -> None:
    """
    Purpose: Verify that user message contains the input text from evaluation input.
    Why this matters: Input text provides context for hallucination evaluation.
    Setup summary: Create input with specific text, assert it appears in user message.
    """
    # Arrange
    input_text: str = "What is the capital of France?"
    input_data: EvaluationMetricInput = EvaluationMetricInput(
        input_text=input_text,
        output_text="Output",
    )

    # Act
    result: LanguageModelMessages = _compose_msgs(
        input_data, hallucination_config, has_context=False
    )

    # Assert
    assert input_text in result.root[1].content


@pytest.mark.ai
def test_compose_msgs__includes_output_text__in_user_message(
    hallucination_config: HallucinationConfig,
) -> None:
    """
    Purpose: Verify that user message contains the output text being evaluated.
    Why this matters: Output text is the primary target of hallucination detection.
    Setup summary: Create input with specific output, assert it appears in user message.
    """
    # Arrange
    output_text: str = "The capital is Paris."
    input_data: EvaluationMetricInput = EvaluationMetricInput(
        input_text="Question",
        output_text=output_text,
    )

    # Act
    result: LanguageModelMessages = _compose_msgs(
        input_data, hallucination_config, has_context=False
    )

    # Assert
    assert output_text in result.root[1].content


@pytest.mark.ai
def test_compose_msgs__generates_non_empty_messages__from_config_prompts(
    hallucination_config: HallucinationConfig,
) -> None:
    """
    Purpose: Verify that messages use prompts from config and generate non-empty content.
    Why this matters: Ensures prompt templates are properly rendered.
    Setup summary: Compose messages, assert both system and user messages have content.
    """
    # Arrange
    input_data: EvaluationMetricInput = EvaluationMetricInput(
        input_text="Question",
        output_text="Output",
    )

    # Act
    result: LanguageModelMessages = _compose_msgs(
        input_data, hallucination_config, has_context=True
    )

    # Assert
    assert len(result.root[0].content) > 0
    assert len(result.root[1].content) > 0
