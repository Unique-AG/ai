"""
Unit tests for referencing utilities.
"""

import pytest


@pytest.mark.ai
def test_get_reference_pattern__returns_formatted_sup_tag__with_single_digit() -> None:
    """
    Purpose: Verify get_reference_pattern creates correct HTML sup tag format.
    Why this matters: Ensures consistent reference formatting across the system.
    Setup summary: Call with single digit, assert proper HTML sup tag structure.
    """
    # Arrange
    from unique_toolkit._common.referencing import get_reference_pattern

    ref_number = 1

    # Act
    result = get_reference_pattern(ref_number)

    # Assert
    assert result == "<sup>1</sup>"
    assert isinstance(result, str)


@pytest.mark.ai
def test_get_reference_pattern__returns_formatted_sup_tag__with_multi_digit() -> None:
    """
    Purpose: Verify get_reference_pattern handles multi-digit reference numbers.
    Why this matters: Support for documents with many references (10+).
    Setup summary: Call with multi-digit number, assert proper formatting.
    """
    # Arrange
    from unique_toolkit._common.referencing import get_reference_pattern

    ref_number = 42

    # Act
    result = get_reference_pattern(ref_number)

    # Assert
    assert result == "<sup>42</sup>"


@pytest.mark.ai
def test_get_all_ref_numbers__returns_sorted_unique_list__with_multiple_refs() -> None:
    """
    Purpose: Verify get_all_ref_numbers extracts and sorts all reference numbers.
    Why this matters: Enables reference validation and manipulation across text.
    Setup summary: Provide text with multiple references, assert sorted unique list.
    """
    # Arrange
    from unique_toolkit._common.referencing import get_all_ref_numbers

    text = (
        "Some text<sup>3</sup> with <sup>1</sup> multiple<sup>3</sup> refs<sup>2</sup>."
    )

    # Act
    result = get_all_ref_numbers(text)

    # Assert
    assert result == [1, 2, 3]
    assert isinstance(result, list)


@pytest.mark.ai
def test_get_all_ref_numbers__returns_empty_list__with_no_refs() -> None:
    """
    Purpose: Verify get_all_ref_numbers handles text without references.
    Why this matters: Prevents errors when processing unreferenced text.
    Setup summary: Provide text without references, assert empty list.
    """
    # Arrange
    from unique_toolkit._common.referencing import get_all_ref_numbers

    text = "Some text without any references."

    # Act
    result = get_all_ref_numbers(text)

    # Assert
    assert result == []


@pytest.mark.ai
def test_get_all_ref_numbers__handles_whitespace__in_sup_tags() -> None:
    """
    Purpose: Verify get_all_ref_numbers tolerates whitespace in sup tags.
    Why this matters: Handles malformed or pretty-printed HTML gracefully.
    Setup summary: Provide references with internal whitespace, assert correct extraction.
    """
    # Arrange
    from unique_toolkit._common.referencing import get_all_ref_numbers

    text = "Text<sup> 1 </sup> with <sup>  2  </sup> spaced refs."

    # Act
    result = get_all_ref_numbers(text)

    # Assert
    assert result == [1, 2]


@pytest.mark.ai
def test_get_max_ref_number__returns_highest_number__with_multiple_refs() -> None:
    """
    Purpose: Verify get_max_ref_number identifies the maximum reference number.
    Why this matters: Essential for generating new reference numbers sequentially.
    Setup summary: Provide text with multiple references, assert max value returned.
    """
    # Arrange
    from unique_toolkit._common.referencing import get_max_ref_number

    text = "Text<sup>5</sup> with <sup>10</sup> multiple<sup>2</sup> refs."

    # Act
    result = get_max_ref_number(text)

    # Assert
    assert result == 10


@pytest.mark.ai
def test_get_max_ref_number__returns_none__with_no_refs() -> None:
    """
    Purpose: Verify get_max_ref_number returns None for text without references.
    Why this matters: Enables proper handling of unreferenced text.
    Setup summary: Provide text without references, assert None returned.
    """
    # Arrange
    from unique_toolkit._common.referencing import get_max_ref_number

    text = "Text without any references."

    # Act
    result = get_max_ref_number(text)

    # Assert
    assert result is None


@pytest.mark.ai
def test_replace_ref_number__replaces_with_int__single_occurrence() -> None:
    """
    Purpose: Verify replace_ref_number replaces reference with new integer.
    Why this matters: Enables reference renumbering during text processing.
    Setup summary: Replace one reference with integer, assert proper substitution.
    """
    # Arrange
    from unique_toolkit._common.referencing import replace_ref_number

    text = "Some text<sup>1</sup> here."

    # Act
    result = replace_ref_number(text, ref_number=1, replacement=5)

    # Assert
    assert result == "Some text<sup>5</sup> here."


@pytest.mark.ai
def test_replace_ref_number__replaces_with_string__single_occurrence() -> None:
    """
    Purpose: Verify replace_ref_number can replace with arbitrary string.
    Why this matters: Allows flexible reference transformation beyond renumbering.
    Setup summary: Replace reference with string, assert exact substitution.
    """
    # Arrange
    from unique_toolkit._common.referencing import replace_ref_number

    text = "Some text<sup>1</sup> here."

    # Act
    result = replace_ref_number(text, ref_number=1, replacement="[REF]")

    # Assert
    assert result == "Some text[REF] here."


@pytest.mark.ai
def test_replace_ref_number__replaces_all_occurrences__of_same_number() -> None:
    """
    Purpose: Verify replace_ref_number replaces all instances of target reference.
    Why this matters: Ensures consistent reference updates throughout text.
    Setup summary: Provide text with duplicate reference, assert all replaced.
    """
    # Arrange
    from unique_toolkit._common.referencing import replace_ref_number

    text = "Text<sup>2</sup> with <sup>2</sup> duplicate refs<sup>2</sup>."

    # Act
    result = replace_ref_number(text, ref_number=2, replacement=9)

    # Assert
    assert result == "Text<sup>9</sup> with <sup>9</sup> duplicate refs<sup>9</sup>."


@pytest.mark.ai
def test_replace_ref_number__preserves_other_refs__when_replacing() -> None:
    """
    Purpose: Verify replace_ref_number only modifies target reference number.
    Why this matters: Prevents unintended side effects on other references.
    Setup summary: Replace one reference among many, assert others unchanged.
    """
    # Arrange
    from unique_toolkit._common.referencing import replace_ref_number

    text = "Text<sup>1</sup> with <sup>2</sup> and <sup>3</sup>."

    # Act
    result = replace_ref_number(text, ref_number=2, replacement=7)

    # Assert
    assert result == "Text<sup>1</sup> with <sup>7</sup> and <sup>3</sup>."


@pytest.mark.ai
def test_replace_ref_number__handles_whitespace__in_target_ref() -> None:
    """
    Purpose: Verify replace_ref_number matches references with internal whitespace.
    Why this matters: Ensures robust matching of malformed HTML.
    Setup summary: Replace reference with whitespace, assert successful replacement.
    """
    # Arrange
    from unique_toolkit._common.referencing import replace_ref_number

    text = "Text<sup> 3 </sup> with spacing."

    # Act
    result = replace_ref_number(text, ref_number=3, replacement=5)

    # Assert
    assert result == "Text<sup>5</sup> with spacing."


@pytest.mark.ai
def test_remove_ref_number__removes_single_ref__completely() -> None:
    """
    Purpose: Verify remove_ref_number deletes target reference from text.
    Why this matters: Enables reference cleanup during text processing.
    Setup summary: Remove one reference, assert it's deleted without trace.
    """
    # Arrange
    from unique_toolkit._common.referencing import remove_ref_number

    text = "Some text<sup>1</sup> here."

    # Act
    result = remove_ref_number(text, ref_number=1)

    # Assert
    assert result == "Some text here."


@pytest.mark.ai
def test_remove_ref_number__removes_all_occurrences__of_same_number() -> None:
    """
    Purpose: Verify remove_ref_number removes all instances of target reference.
    Why this matters: Ensures complete cleanup of duplicate references.
    Setup summary: Remove reference appearing multiple times, assert all removed.
    """
    # Arrange
    from unique_toolkit._common.referencing import remove_ref_number

    text = "Text<sup>2</sup> with <sup>2</sup> duplicate<sup>2</sup>."

    # Act
    result = remove_ref_number(text, ref_number=2)

    # Assert
    assert result == "Text with  duplicate."


@pytest.mark.ai
def test_remove_ref_number__preserves_other_refs__when_removing() -> None:
    """
    Purpose: Verify remove_ref_number only deletes target reference number.
    Why this matters: Prevents accidental deletion of other references.
    Setup summary: Remove one reference among many, assert others remain.
    """
    # Arrange
    from unique_toolkit._common.referencing import remove_ref_number

    text = "Text<sup>1</sup> with <sup>2</sup> and <sup>3</sup>."

    # Act
    result = remove_ref_number(text, ref_number=2)

    # Assert
    assert result == "Text<sup>1</sup> with  and <sup>3</sup>."


@pytest.mark.ai
def test_remove_all_refs__removes_all_references__from_text() -> None:
    """
    Purpose: Verify remove_all_refs strips all sup tags from text.
    Why this matters: Enables generation of clean, unreferenced text copies.
    Setup summary: Provide text with multiple references, assert all removed.
    """
    # Arrange
    from unique_toolkit._common.referencing import remove_all_refs

    text = "Text<sup>1</sup> with <sup>2</sup> multiple<sup>3</sup> refs."

    # Act
    result = remove_all_refs(text)

    # Assert
    assert result == "Text with  multiple refs."


@pytest.mark.ai
def test_remove_all_refs__returns_unchanged__with_no_refs() -> None:
    """
    Purpose: Verify remove_all_refs handles unreferenced text correctly.
    Why this matters: Ensures function is safe to call on any text.
    Setup summary: Provide text without references, assert unchanged.
    """
    # Arrange
    from unique_toolkit._common.referencing import remove_all_refs

    text = "Plain text without references."

    # Act
    result = remove_all_refs(text)

    # Assert
    assert result == "Plain text without references."


@pytest.mark.ai
def test_remove_all_refs__handles_whitespace__in_all_refs() -> None:
    """
    Purpose: Verify remove_all_refs handles references with internal whitespace.
    Why this matters: Ensures robust cleanup of malformed HTML.
    Setup summary: Provide references with spacing, assert all removed.
    """
    # Arrange
    from unique_toolkit._common.referencing import remove_all_refs

    text = "Text<sup> 1 </sup> with <sup>  2  </sup> spaced."

    # Act
    result = remove_all_refs(text)

    # Assert
    assert result == "Text with  spaced."


@pytest.mark.ai
def test_remove_consecutive_ref_space__removes_spaces__between_refs() -> None:
    """
    Purpose: Verify remove_consecutive_ref_space collapses spaces between adjacent refs.
    Why this matters: Improves visual formatting of multiple citations.
    Setup summary: Provide consecutive references with spaces, assert spaces removed.
    """
    # Arrange
    from unique_toolkit._common.referencing import remove_consecutive_ref_space

    text = "Text<sup>1</sup> <sup>2</sup> with spaces."

    # Act
    result = remove_consecutive_ref_space(text)

    # Assert
    assert result == "Text<sup>1</sup><sup>2</sup> with spaces."


@pytest.mark.ai
def test_remove_consecutive_ref_space__handles_multiple_spaces__between_refs() -> None:
    """
    Purpose: Verify remove_consecutive_ref_space handles multiple spaces.
    Why this matters: Handles various whitespace formatting scenarios.
    Setup summary: Provide references with multiple spaces, assert collapsed.
    """
    # Arrange
    from unique_toolkit._common.referencing import remove_consecutive_ref_space

    text = "Text<sup>1</sup>   <sup>2</sup> and <sup>3</sup>    <sup>4</sup>."

    # Act
    result = remove_consecutive_ref_space(text)

    # Assert
    assert result == "Text<sup>1</sup><sup>2</sup> and <sup>3</sup><sup>4</sup>."


@pytest.mark.ai
def test_remove_consecutive_ref_space__preserves_other_spaces__in_text() -> None:
    """
    Purpose: Verify remove_consecutive_ref_space only affects inter-reference spaces.
    Why this matters: Prevents unwanted text formatting changes.
    Setup summary: Provide text with various spaces, assert only ref spaces removed.
    """
    # Arrange
    from unique_toolkit._common.referencing import remove_consecutive_ref_space

    text = "Some    text<sup>1</sup> <sup>2</sup> has   many  spaces."

    # Act
    result = remove_consecutive_ref_space(text)

    # Assert
    assert result == "Some    text<sup>1</sup><sup>2</sup> has   many  spaces."


@pytest.mark.ai
def test_remove_consecutive_ref_space__returns_unchanged__without_consecutive_refs() -> (
    None
):
    """
    Purpose: Verify remove_consecutive_ref_space leaves non-consecutive refs unchanged.
    Why this matters: Ensures function only modifies adjacent references.
    Setup summary: Provide non-adjacent references, assert unchanged.
    """
    # Arrange
    from unique_toolkit._common.referencing import remove_consecutive_ref_space

    text = "Text<sup>1</sup> words <sup>2</sup> between."

    # Act
    result = remove_consecutive_ref_space(text)

    # Assert
    assert result == "Text<sup>1</sup> words <sup>2</sup> between."


@pytest.mark.ai
@pytest.mark.parametrize(
    "ref_number, expected",
    [
        (0, "<sup>0</sup>"),
        (1, "<sup>1</sup>"),
        (99, "<sup>99</sup>"),
        (999, "<sup>999</sup>"),
    ],
    ids=["zero", "single-digit", "double-digit", "triple-digit"],
)
def test_get_reference_pattern__handles_various_numbers(
    ref_number: int, expected: str
) -> None:
    """
    Purpose: Verify get_reference_pattern works for various number ranges.
    Why this matters: Ensures robustness across different reference counts.
    Setup summary: Parametrized test with different ref numbers.
    """
    # Arrange
    from unique_toolkit._common.referencing import get_reference_pattern

    # Act
    result = get_reference_pattern(ref_number)

    # Assert
    assert result == expected


@pytest.mark.ai
@pytest.mark.parametrize(
    "text, expected",
    [
        ("No refs here", []),
        ("<sup>1</sup>", [1]),
        ("<sup>5</sup><sup>3</sup><sup>1</sup>", [1, 3, 5]),
        ("<sup>1</sup>text<sup>1</sup>", [1]),
        ("<sup>10</sup><sup>20</sup><sup>5</sup>", [5, 10, 20]),
    ],
    ids=[
        "no-refs",
        "single-ref",
        "multiple-unordered",
        "duplicate-refs",
        "multi-digit",
    ],
)
def test_get_all_ref_numbers__various_text_formats(
    text: str, expected: list[int]
) -> None:
    """
    Purpose: Table-driven test for reference extraction across formats.
    Why this matters: Ensures consistent behavior across different text patterns.
    Setup summary: Parametrized inputs with expected sorted unique results.
    """
    # Arrange
    from unique_toolkit._common.referencing import get_all_ref_numbers

    # Act
    result = get_all_ref_numbers(text)

    # Assert
    assert result == expected


@pytest.mark.ai
@pytest.mark.parametrize(
    "text, expected",
    [
        ("No refs", None),
        ("<sup>1</sup>", 1),
        ("<sup>100</sup><sup>50</sup><sup>25</sup>", 100),
        ("<sup>5</sup> and <sup>10</sup>", 10),
    ],
    ids=["no-refs-returns-none", "single-ref", "unordered-multi-digit", "simple-multi"],
)
def test_get_max_ref_number__various_scenarios(text: str, expected: int | None) -> None:
    """
    Purpose: Table-driven test for max reference number extraction.
    Why this matters: Validates max finding logic across edge cases.
    Setup summary: Parametrized test with various reference patterns.
    """
    # Arrange
    from unique_toolkit._common.referencing import get_max_ref_number

    # Act
    result = get_max_ref_number(text)

    # Assert
    assert result == expected
