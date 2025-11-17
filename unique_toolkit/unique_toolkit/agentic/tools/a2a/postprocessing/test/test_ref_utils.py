"""
Unit tests for reference utility functions in _ref_utils.py.
"""

import pytest

from unique_toolkit.agentic.tools.a2a.postprocessing._ref_utils import (
    _add_source_ids,
    add_content_refs,
    add_content_refs_and_replace_in_text,
)
from unique_toolkit.content import ContentReference

# Fixtures


@pytest.fixture
def base_content_ref() -> ContentReference:
    """Base ContentReference fixture for testing."""
    return ContentReference(
        name="Test Doc",
        url="https://example.com/doc1",
        sequence_number=1,
        source_id="doc-123",
        source="test-source",
        description="Test document description",
    )


@pytest.fixture
def content_refs_list() -> list[ContentReference]:
    """List of ContentReference fixtures."""
    return [
        ContentReference(
            name="Doc 1",
            url="https://example.com/doc1",
            sequence_number=1,
            source_id="doc-1",
            source="test-source",
            description="Document 1 description",
        ),
        ContentReference(
            name="Doc 2",
            url="https://example.com/doc2",
            sequence_number=2,
            source_id="doc-2",
            source="test-source",
            description="Document 2 description",
        ),
    ]


# Tests for _add_source_ids


@pytest.mark.ai
def test_add_source_ids__returns_empty_dict__when_no_new_refs() -> None:
    """
    Purpose: Verify _add_source_ids returns empty dict when no new references provided.
    Why this matters: Ensures function handles empty input gracefully.
    Setup summary: Empty new_refs iterable, assert empty result dict.
    """
    # Arrange
    existing_refs = {"doc-1": 1, "doc-2": 2}
    new_refs: list[str] = []

    # Act
    result = _add_source_ids(existing_refs, new_refs)

    # Assert
    assert result == {}
    assert isinstance(result, dict)


@pytest.mark.ai
def test_add_source_ids__assigns_sequential_numbers__for_new_source_ids() -> None:
    """
    Purpose: Verify _add_source_ids assigns sequential numbers starting after max existing.
    Why this matters: Core functionality for maintaining reference number uniqueness.
    Setup summary: Existing refs with max=2, add two new IDs, verify they get 3 and 4.
    """
    # Arrange
    existing_refs = {"doc-1": 1, "doc-2": 2}
    new_refs = ["doc-3", "doc-4"]

    # Act
    result = _add_source_ids(existing_refs, new_refs)

    # Assert
    assert result == {"doc-3": 3, "doc-4": 4}


@pytest.mark.ai
def test_add_source_ids__skips_existing_source_ids__does_not_duplicate() -> None:
    """
    Purpose: Verify _add_source_ids skips source IDs that already exist.
    Why this matters: Prevents duplicate references and maintains reference integrity.
    Setup summary: New refs include existing ID, verify it's not in result.
    """
    # Arrange
    existing_refs = {"doc-1": 1, "doc-2": 2}
    new_refs = ["doc-1", "doc-3"]

    # Act
    result = _add_source_ids(existing_refs, new_refs)

    # Assert
    assert result == {"doc-3": 3}
    assert "doc-1" not in result


@pytest.mark.ai
def test_add_source_ids__handles_empty_existing_refs__starts_at_one() -> None:
    """
    Purpose: Verify _add_source_ids starts numbering at 1 when no existing refs.
    Why this matters: Ensures correct initialization for new reference collections.
    Setup summary: Empty existing_refs, add new refs, verify numbering starts at 1.
    """
    # Arrange
    existing_refs: dict[str, int] = {}
    new_refs = ["doc-1", "doc-2"]

    # Act
    result = _add_source_ids(existing_refs, new_refs)

    # Assert
    assert result == {"doc-1": 1, "doc-2": 2}


@pytest.mark.ai
def test_add_source_ids__handles_duplicate_in_new_refs__assigns_once() -> None:
    """
    Purpose: Verify _add_source_ids handles duplicates within new_refs correctly.
    Why this matters: Prevents multiple assignments for same source ID in a batch.
    Setup summary: New refs with duplicates, verify only one sequence number assigned.
    """
    # Arrange
    existing_refs: dict[str, int] = {}
    new_refs = ["doc-1", "doc-2", "doc-1", "doc-3"]

    # Act
    result = _add_source_ids(existing_refs, new_refs)

    # Assert
    assert result == {"doc-1": 1, "doc-2": 2, "doc-3": 3}


# Tests for add_content_refs


@pytest.mark.ai
def test_add_content_refs__returns_original_list__when_no_new_refs(
    content_refs_list: list[ContentReference],
) -> None:
    """
    Purpose: Verify add_content_refs returns original list unchanged when no new refs.
    Why this matters: Handles empty additions efficiently without modification.
    Setup summary: Existing refs, empty new refs list, assert original returned.
    """
    # Arrange
    new_refs: list[ContentReference] = []

    # Act
    result = add_content_refs(content_refs_list, new_refs)

    # Assert
    assert result == content_refs_list
    assert len(result) == 2


@pytest.mark.ai
def test_add_content_refs__appends_new_refs__with_updated_sequence_numbers(
    content_refs_list: list[ContentReference],
) -> None:
    """
    Purpose: Verify add_content_refs appends new refs with correct sequence numbers.
    Why this matters: Core functionality for extending reference lists.
    Setup summary: Two existing refs (seq 1,2), add one new, verify seq 3 assigned.
    """
    # Arrange
    new_ref = ContentReference(
        name="Doc 3",
        url="https://example.com/doc3",
        sequence_number=1,  # Original number, should be updated
        source_id="doc-3",
        source="test-source",
        description="Document 3 description",
    )
    new_refs = [new_ref]

    # Act
    result = add_content_refs(content_refs_list, new_refs)

    # Assert
    assert len(result) == 3
    assert result[2].source_id == "doc-3"
    assert result[2].sequence_number == 3


@pytest.mark.ai
def test_add_content_refs__skips_duplicate_source_ids__no_duplication(
    content_refs_list: list[ContentReference],
) -> None:
    """
    Purpose: Verify add_content_refs skips refs with existing source_ids.
    Why this matters: Prevents duplicate references in the final list.
    Setup summary: New ref with existing source_id, verify not added again.
    """
    # Arrange
    duplicate_ref = ContentReference(
        name="Doc 1 Duplicate",
        url="https://example.com/doc1-dup",
        sequence_number=99,
        source_id="doc-1",  # Already exists
        source="test-source",
        description="Duplicate document description",
    )
    new_refs = [duplicate_ref]

    # Act
    result = add_content_refs(content_refs_list, new_refs)

    # Assert
    assert len(result) == 2  # No new item added
    assert all(ref.source_id != "doc-1" or ref.name == "Doc 1" for ref in result)


@pytest.mark.ai
def test_add_content_refs__handles_multiple_new_refs__sequential_numbering() -> None:
    """
    Purpose: Verify add_content_refs handles multiple new refs with sequential numbering.
    Why this matters: Ensures batch additions maintain sequence integrity.
    Setup summary: Add three new refs, verify they get sequential numbers 1, 2, 3.
    """
    # Arrange
    message_refs: list[ContentReference] = []
    new_refs = [
        ContentReference(
            name="Doc A",
            url="https://example.com/a",
            sequence_number=10,
            source_id="doc-a",
            source="test",
            description="Document A description",
        ),
        ContentReference(
            name="Doc B",
            url="https://example.com/b",
            sequence_number=20,
            source_id="doc-b",
            source="test",
            description="Document B description",
        ),
        ContentReference(
            name="Doc C",
            url="https://example.com/c",
            sequence_number=30,
            source_id="doc-c",
            source="test",
            description="Document C description",
        ),
    ]

    # Act
    result = add_content_refs(message_refs, new_refs)

    # Assert
    assert len(result) == 3
    assert result[0].sequence_number == 1
    assert result[1].sequence_number == 2
    assert result[2].sequence_number == 3


@pytest.mark.ai
def test_add_content_refs__preserves_original_ref_properties__except_sequence_num(
    content_refs_list: list[ContentReference],
) -> None:
    """
    Purpose: Verify add_content_refs preserves all properties except sequence_number.
    Why this matters: Ensures reference data integrity during addition.
    Setup summary: Add ref with specific properties, verify all preserved with new seq num.
    """
    # Arrange
    new_ref = ContentReference(
        name="Special Doc",
        url="https://example.com/special",
        sequence_number=999,
        source_id="doc-special",
        source="special-source",
        id="custom-id",
        message_id="msg-123",
        original_index=[1, 2, 3],
        description="Special document description",
    )
    new_refs = [new_ref]

    # Act
    result = add_content_refs(content_refs_list, new_refs)

    # Assert
    added_ref = result[2]
    assert added_ref.name == "Special Doc"
    assert added_ref.url == "https://example.com/special"
    assert added_ref.source_id == "doc-special"
    assert added_ref.source == "special-source"
    assert added_ref.id == "custom-id"
    assert added_ref.message_id == "msg-123"
    assert added_ref.original_index == [1, 2, 3]
    assert added_ref.sequence_number == 3  # Updated


@pytest.mark.ai
def test_add_content_refs__sorts_new_refs_by_sequence_number__before_processing() -> (
    None
):
    """
    Purpose: Verify add_content_refs processes new refs in sequence_number order.
    Why this matters: Ensures predictable ordering when multiple refs added.
    Setup summary: Add refs in unsorted order, verify they're assigned by original seq order.
    """
    # Arrange
    message_refs: list[ContentReference] = []
    new_refs = [
        ContentReference(
            name="Third",
            url="",
            sequence_number=30,
            source_id="doc-c",
            source="test",
            description="Third document description",
        ),
        ContentReference(
            name="First",
            url="",
            sequence_number=10,
            source_id="doc-a",
            source="test",
            description="First document description",
        ),
        ContentReference(
            name="Second",
            url="",
            sequence_number=20,
            source_id="doc-b",
            source="test",
            description="Second document description",
        ),
    ]

    # Act
    result = add_content_refs(message_refs, new_refs)

    # Assert
    assert len(result) == 3
    # doc-a (seq 10) should be processed first and assigned 1
    assert result[0].source_id == "doc-a"
    assert result[0].sequence_number == 1


# Tests for add_content_refs_and_replace_in_text


@pytest.mark.ai
def test_add_content_refs_and_replace_in_text__returns_unchanged__when_no_new_refs() -> (
    None
):
    """
    Purpose: Verify function returns unchanged text and refs when no new refs provided.
    Why this matters: Handles empty additions efficiently.
    Setup summary: Text and refs with empty new_refs, verify no changes.
    """
    # Arrange
    message_text = "Some text with <sup>1</sup> reference"
    message_refs = [
        ContentReference(
            name="Doc 1",
            url="https://example.com",
            sequence_number=1,
            source_id="doc-1",
            source="test",
            description="Document 1 description",
        )
    ]
    new_refs: list[ContentReference] = []

    # Act
    result_text, result_refs = add_content_refs_and_replace_in_text(
        message_text, message_refs, new_refs
    )

    # Assert
    assert result_text == message_text
    assert result_refs == message_refs


@pytest.mark.ai
def test_add_content_refs_and_replace_in_text__replaces_ref_numbers__in_text() -> None:
    """
    Purpose: Verify function replaces reference numbers in text with updated numbers.
    Why this matters: Maintains text-reference synchronization.
    Setup summary: Text with <sup>1</sup>, add new ref that renumbers it, verify replacement.
    """
    # Arrange
    message_text = "Check this reference <sup>1</sup> here"
    message_refs: list[ContentReference] = []
    new_refs = [
        ContentReference(
            name="Doc 1",
            url="https://example.com/doc1",
            sequence_number=1,
            source_id="doc-1",
            source="test",
            description="Document 1 description",
        )
    ]

    # Act
    result_text, result_refs = add_content_refs_and_replace_in_text(
        message_text, message_refs, new_refs
    )

    # Assert
    assert "<sup>1</sup>" in result_text
    assert len(result_refs) == 1


@pytest.mark.ai
def test_add_content_refs_and_replace_in_text__uses_custom_pattern_functions(
    mocker,
) -> None:
    """
    Purpose: Verify function uses custom pattern and replacement functions when provided.
    Why this matters: Allows flexibility for different reference formats.
    Setup summary: Mock pattern functions with regex-escaped patterns, verify they're called correctly.
    """
    # Arrange
    # Use regex-escaped pattern since replace_in_text uses re.sub
    message_text = "[REF-1] is here"
    message_refs: list[ContentReference] = []
    new_refs = [
        ContentReference(
            name="Doc 1",
            url="",
            sequence_number=1,
            source_id="doc-1",
            source="test",
            description="Document 1 description",
        )
    ]

    def custom_pattern(num: int) -> str:
        # Return regex-escaped pattern
        return f"\\[REF-{num}\\]"

    def custom_replacement(num: int) -> str:
        return f"[REF-{num}]"

    mock_pattern = mocker.Mock(side_effect=custom_pattern)
    mock_replacement = mocker.Mock(side_effect=custom_replacement)

    # Act
    result_text, result_refs = add_content_refs_and_replace_in_text(
        message_text,
        message_refs,
        new_refs,
        ref_pattern_f=mock_pattern,
        ref_replacement_f=mock_replacement,
    )

    # Assert
    mock_pattern.assert_called_once_with(1)
    mock_replacement.assert_called_once_with(1)
    assert len(result_refs) == 1
    assert result_text == "[REF-1] is here"


@pytest.mark.ai
def test_add_content_refs_and_replace_in_text__handles_multiple_refs_in_text() -> None:
    """
    Purpose: Verify function correctly handles multiple reference replacements in text.
    Why this matters: Ensures batch text updates work correctly.
    Setup summary: Text with multiple refs, add new refs, verify all updated.
    """
    # Arrange
    message_text = "First <sup>1</sup> and second <sup>2</sup>"
    message_refs: list[ContentReference] = []
    new_refs = [
        ContentReference(
            name="Doc 1",
            url="",
            sequence_number=1,
            source_id="doc-1",
            source="test",
            description="Document 1 description",
        ),
        ContentReference(
            name="Doc 2",
            url="",
            sequence_number=2,
            source_id="doc-2",
            source="test",
            description="Document 2 description",
        ),
    ]

    # Act
    result_text, result_refs = add_content_refs_and_replace_in_text(
        message_text, message_refs, new_refs
    )

    # Assert
    assert "<sup>1</sup>" in result_text
    assert "<sup>2</sup>" in result_text
    assert len(result_refs) == 2


@pytest.mark.ai
def test_add_content_refs_and_replace_in_text__avoids_duplicate_source_ids() -> None:
    """
    Purpose: Verify function doesn't add refs with duplicate source_ids.
    Why this matters: Maintains reference uniqueness in combined operation.
    Setup summary: Try to add ref with existing source_id, verify not duplicated.
    """
    # Arrange
    message_text = "Text with <sup>1</sup>"
    message_refs = [
        ContentReference(
            name="Doc 1",
            url="",
            sequence_number=1,
            source_id="doc-1",
            source="test",
            description="Document 1 description",
        )
    ]
    new_refs = [
        ContentReference(
            name="Doc 1 Duplicate",
            url="",
            sequence_number=2,
            source_id="doc-1",  # Duplicate
            source="test",
            description="Duplicate document description",
        )
    ]

    # Act
    result_text, result_refs = add_content_refs_and_replace_in_text(
        message_text, message_refs, new_refs
    )

    # Assert
    assert len(result_refs) == 1  # No duplicate added
    assert result_text == message_text


@pytest.mark.ai
def test_add_content_refs_and_replace_in_text__returns_tuple_with_correct_types() -> (
    None
):
    """
    Purpose: Verify function returns correctly typed tuple.
    Why this matters: Ensures API contract and type safety.
    Setup summary: Call function, assert return types are str and list.
    """
    # Arrange
    message_text = "Test"
    message_refs: list[ContentReference] = []
    new_refs: list[ContentReference] = []

    # Act
    result_text, result_refs = add_content_refs_and_replace_in_text(
        message_text, message_refs, new_refs
    )

    # Assert
    assert isinstance(result_text, str)
    assert isinstance(result_refs, list)


@pytest.mark.ai
def test_add_content_refs_and_replace_in_text__creates_ref_map_correctly() -> None:
    """
    Purpose: Verify function creates correct mapping for text replacement.
    Why this matters: Ensures reference renumbering logic is correct.
    Setup summary: Add refs that need renumbering, verify text updates accordingly.
    """
    # Arrange
    # Start with existing ref at sequence 1
    message_text = "See <sup>5</sup> for details"
    message_refs = [
        ContentReference(
            name="Existing",
            url="",
            sequence_number=1,
            source_id="doc-existing",
            source="test",
            description="Existing document description",
        )
    ]
    # Add new ref with sequence 5 that should become sequence 2
    new_refs = [
        ContentReference(
            name="New Doc",
            url="",
            sequence_number=5,
            source_id="doc-new",
            source="test",
            description="New document description",
        )
    ]

    # Act
    result_text, result_refs = add_content_refs_and_replace_in_text(
        message_text, message_refs, new_refs
    )

    # Assert
    # The new ref's sequence number 5 should be mapped to 2
    assert len(result_refs) == 2
    assert result_refs[1].sequence_number == 2
    # Text should have <sup>5</sup> replaced with <sup>2</sup>
    assert "<sup>2</sup>" in result_text
    assert "<sup>5</sup>" not in result_text
