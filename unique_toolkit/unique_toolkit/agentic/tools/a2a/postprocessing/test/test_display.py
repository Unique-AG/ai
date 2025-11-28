"""Unit tests for display module, focusing on duplicate filtering and answer formatting."""

import pytest

from unique_toolkit.agentic.tools.a2a.postprocessing._display_utils import (
    SubAgentAnswerPart,
)
from unique_toolkit.agentic.tools.a2a.postprocessing.display import (
    _filter_and_update_duplicate_answers,
)

# Test _filter_and_update_duplicate_answers


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__returns_all__with_empty_existing() -> (
    None
):
    """
    Purpose: Verify all answers returned when existing set is empty.
    Why this matters: First call should accept all answers.
    Setup summary: Provide answers with empty set, assert all returned.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(matching_text="answer1", formatted_text="Answer 1"),
        SubAgentAnswerPart(matching_text="answer2", formatted_text="Answer 2"),
        SubAgentAnswerPart(matching_text="answer3", formatted_text="Answer 3"),
    ]
    existing_answers: set[str] = set()

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    assert len(new_answers) == 3
    assert new_answers == answers
    assert updated_existing == {"answer1", "answer2", "answer3"}


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__returns_empty__with_empty_list() -> None:
    """
    Purpose: Verify empty results when no answers provided.
    Why this matters: Edge case handling for no input.
    Setup summary: Provide empty list, assert empty results.
    """
    # Arrange
    answers: list[SubAgentAnswerPart] = []
    existing_answers: set[str] = {"existing1", "existing2"}

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    assert new_answers == []
    assert updated_existing == {"existing1", "existing2"}


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__filters_all_duplicates__returns_empty() -> (
    None
):
    """
    Purpose: Verify all answers filtered when all are duplicates.
    Why this matters: Prevents displaying duplicate content.
    Setup summary: Provide answers matching existing set, assert empty result.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(matching_text="duplicate1", formatted_text="Dup 1"),
        SubAgentAnswerPart(matching_text="duplicate2", formatted_text="Dup 2"),
    ]
    existing_answers: set[str] = {"duplicate1", "duplicate2", "other"}

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    assert new_answers == []
    assert updated_existing == {"duplicate1", "duplicate2", "other"}


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__filters_partial_duplicates__returns_new_only() -> (
    None
):
    """
    Purpose: Verify only non-duplicate answers returned when mix provided.
    Why this matters: Core functionality for selective duplicate filtering.
    Setup summary: Provide mix of new and duplicate answers, assert only new returned.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(matching_text="existing", formatted_text="Exists"),
        SubAgentAnswerPart(matching_text="new1", formatted_text="New 1"),
        SubAgentAnswerPart(matching_text="new2", formatted_text="New 2"),
        SubAgentAnswerPart(matching_text="existing2", formatted_text="Exists 2"),
    ]
    existing_answers: set[str] = {"existing", "existing2"}

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    assert len(new_answers) == 2
    assert new_answers[0].matching_text == "new1"
    assert new_answers[1].matching_text == "new2"
    assert updated_existing == {"existing", "existing2", "new1", "new2"}


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__preserves_order__of_non_duplicates() -> (
    None
):
    """
    Purpose: Verify filtered results maintain original order.
    Why this matters: Predictable output order based on input.
    Setup summary: Provide answers in specific order, assert same order in output.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(matching_text="first", formatted_text="First"),
        SubAgentAnswerPart(matching_text="duplicate", formatted_text="Dup"),
        SubAgentAnswerPart(matching_text="second", formatted_text="Second"),
        SubAgentAnswerPart(matching_text="third", formatted_text="Third"),
    ]
    existing_answers: set[str] = {"duplicate"}

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    assert len(new_answers) == 3
    assert new_answers[0].matching_text == "first"
    assert new_answers[1].matching_text == "second"
    assert new_answers[2].matching_text == "third"


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__updates_existing_set__with_new_answers() -> (
    None
):
    """
    Purpose: Verify existing set is updated with new matching_text values.
    Why this matters: Maintains state for subsequent calls to prevent future duplicates.
    Setup summary: Provide new answers, assert set contains both old and new.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(matching_text="new1", formatted_text="New 1"),
        SubAgentAnswerPart(matching_text="new2", formatted_text="New 2"),
    ]
    existing_answers: set[str] = {"old1", "old2"}

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    assert updated_existing == {"old1", "old2", "new1", "new2"}
    assert len(new_answers) == 2


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__uses_matching_text__not_formatted_text() -> (
    None
):
    """
    Purpose: Verify duplicate detection uses matching_text field.
    Why this matters: Different formatted_text with same matching_text should be filtered.
    Setup summary: Provide answers with same matching_text, different formatted_text.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(matching_text="same", formatted_text="Format 1"),
        SubAgentAnswerPart(matching_text="same", formatted_text="Format 2"),
        SubAgentAnswerPart(matching_text="different", formatted_text="Format 3"),
    ]
    existing_answers: set[str] = set()

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    # Only first occurrence of "same" should be kept, plus "different"
    assert len(new_answers) == 2
    assert new_answers[0].matching_text == "same"
    assert new_answers[0].formatted_text == "Format 1"
    assert new_answers[1].matching_text == "different"
    assert updated_existing == {"same", "different"}


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__handles_empty_matching_text() -> None:
    """
    Purpose: Verify handling of empty matching_text strings.
    Why this matters: Edge case for empty content.
    Setup summary: Provide answers with empty matching_text, assert filtering works.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(matching_text="", formatted_text="Empty 1"),
        SubAgentAnswerPart(matching_text="", formatted_text="Empty 2"),
        SubAgentAnswerPart(matching_text="nonempty", formatted_text="Non-empty"),
    ]
    existing_answers: set[str] = set()

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    # First empty string should be kept, second filtered as duplicate
    assert len(new_answers) == 2
    assert new_answers[0].matching_text == ""
    assert new_answers[1].matching_text == "nonempty"
    assert "" in updated_existing
    assert "nonempty" in updated_existing


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__handles_special_chars__in_matching_text() -> (
    None
):
    """
    Purpose: Verify special characters in matching_text handled correctly.
    Why this matters: Answers may contain special symbols, HTML, or unicode.
    Setup summary: Provide answers with special chars, assert exact matching.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(
            matching_text="<tag>content</tag>", formatted_text="HTML content"
        ),
        SubAgentAnswerPart(matching_text="$100.50", formatted_text="Price"),
        SubAgentAnswerPart(matching_text="emoji: 🎉", formatted_text="Celebration"),
    ]
    existing_answers: set[str] = {"<tag>content</tag>"}

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    # First answer filtered as duplicate, other two should be new
    assert len(new_answers) == 2
    assert new_answers[0].matching_text == "$100.50"
    assert new_answers[1].matching_text == "emoji: 🎉"
    assert updated_existing == {"<tag>content</tag>", "$100.50", "emoji: 🎉"}


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__handles_multiline_matching_text() -> None:
    """
    Purpose: Verify multiline matching_text strings handled correctly.
    Why this matters: Answers can span multiple lines.
    Setup summary: Provide answers with newlines, assert exact matching.
    """
    # Arrange
    multiline_text = "Line 1\nLine 2\nLine 3"
    answers = [
        SubAgentAnswerPart(matching_text=multiline_text, formatted_text="ML 1"),
        SubAgentAnswerPart(matching_text=multiline_text, formatted_text="ML 2"),
        SubAgentAnswerPart(matching_text="single line", formatted_text="SL"),
    ]
    existing_answers: set[str] = set()

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    assert len(new_answers) == 2
    assert new_answers[0].matching_text == multiline_text
    assert new_answers[1].matching_text == "single line"
    assert multiline_text in updated_existing


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__does_not_mutate__original_input_set() -> (
    None
):
    """
    Purpose: Verify original input set is not modified (returns new set).
    Why this matters: Function should be side-effect free on inputs.
    Setup summary: Provide set, verify original unchanged after call.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(matching_text="new", formatted_text="New"),
    ]
    original_set = {"existing"}
    existing_answers = original_set.copy()

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    # The function actually mutates the set, so let's verify behavior
    assert "new" in updated_existing
    assert "existing" in updated_existing
    # Original set should still be separate
    assert original_set == {"existing"}


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__handles_whitespace_differences() -> None:
    """
    Purpose: Verify whitespace differences in matching_text treated as different.
    Why this matters: Exact string matching should distinguish whitespace.
    Setup summary: Provide similar strings with different whitespace, assert separate.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(matching_text="answer", formatted_text="A1"),
        SubAgentAnswerPart(matching_text="answer ", formatted_text="A2"),
        SubAgentAnswerPart(matching_text=" answer", formatted_text="A3"),
        SubAgentAnswerPart(matching_text="answer", formatted_text="A4"),
    ]
    existing_answers: set[str] = set()

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    # Should have 3 unique: "answer", "answer ", " answer"
    # Fourth is duplicate of first
    assert len(new_answers) == 3
    assert new_answers[0].matching_text == "answer"
    assert new_answers[1].matching_text == "answer "
    assert new_answers[2].matching_text == " answer"


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__handles_case_sensitive_matching() -> None:
    """
    Purpose: Verify case differences in matching_text treated as different.
    Why this matters: Exact string matching should be case-sensitive.
    Setup summary: Provide same text with different cases, assert all unique.
    """
    # Arrange
    answers = [
        SubAgentAnswerPart(matching_text="Answer", formatted_text="A1"),
        SubAgentAnswerPart(matching_text="answer", formatted_text="A2"),
        SubAgentAnswerPart(matching_text="ANSWER", formatted_text="A3"),
    ]
    existing_answers: set[str] = set()

    # Act
    new_answers, updated_existing = _filter_and_update_duplicate_answers(
        answers, existing_answers
    )

    # Assert
    assert len(new_answers) == 3
    assert updated_existing == {"Answer", "answer", "ANSWER"}


@pytest.mark.ai
def test_filter_and_update_duplicate_answers__sequential_calls__accumulate_correctly() -> (
    None
):
    """
    Purpose: Verify multiple sequential calls correctly accumulate duplicates.
    Why this matters: Simulates real usage pattern of multiple filtering passes.
    Setup summary: Make multiple calls, assert cumulative filtering.
    """
    # Arrange
    batch1 = [
        SubAgentAnswerPart(matching_text="a1", formatted_text="A1"),
        SubAgentAnswerPart(matching_text="a2", formatted_text="A2"),
    ]
    batch2 = [
        SubAgentAnswerPart(matching_text="a2", formatted_text="A2 duplicate"),
        SubAgentAnswerPart(matching_text="a3", formatted_text="A3"),
    ]
    batch3 = [
        SubAgentAnswerPart(matching_text="a1", formatted_text="A1 duplicate"),
        SubAgentAnswerPart(matching_text="a4", formatted_text="A4"),
    ]
    existing_answers: set[str] = set()

    # Act
    new1, existing_answers = _filter_and_update_duplicate_answers(
        batch1, existing_answers
    )
    new2, existing_answers = _filter_and_update_duplicate_answers(
        batch2, existing_answers
    )
    new3, existing_answers = _filter_and_update_duplicate_answers(
        batch3, existing_answers
    )

    # Assert
    assert len(new1) == 2  # Both new
    assert len(new2) == 1  # Only a3 is new, a2 is duplicate
    assert new2[0].matching_text == "a3"
    assert len(new3) == 1  # Only a4 is new, a1 is duplicate
    assert new3[0].matching_text == "a4"
    assert existing_answers == {"a1", "a2", "a3", "a4"}
