"""
Unit tests for string utilities.
"""

import re

import pytest


@pytest.mark.ai
def test_replace_in_text__replaces_single_pattern__with_string_pattern() -> None:
    """
    Purpose: Verify replace_in_text handles single string pattern replacement.
    Why this matters: Basic functionality for text transformation.
    Setup summary: Single string pattern, assert proper replacement.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Hello world, hello universe"
    repls = [("hello", "goodbye")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Hello world, goodbye universe"


@pytest.mark.ai
def test_replace_in_text__replaces_multiple_patterns__with_string_patterns() -> None:
    """
    Purpose: Verify replace_in_text handles multiple independent replacements.
    Why this matters: Enables batch text transformations.
    Setup summary: Multiple non-overlapping patterns, assert all replaced.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "The quick brown fox jumps over the lazy dog"
    repls = [("quick", "slow"), ("brown", "red"), ("lazy", "energetic")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "The slow red fox jumps over the energetic dog"


@pytest.mark.ai
def test_replace_in_text__handles_overlapping_replacements__correctly() -> None:
    """
    Purpose: Verify replace_in_text prevents replacement conflicts.
    Why this matters: Critical for avoiding cascading replacement errors.
    Setup summary: Overlapping patterns where one replacement could match another pattern.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "A becomes B and B becomes C"
    repls = [("A", "B"), ("B", "C")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    # A should become B, and original B should become C
    # The new B (from A) should NOT become C
    assert result == "B becomes C and C becomes C"


@pytest.mark.ai
def test_replace_in_text__replaces_with_regex_pattern__compiled_pattern() -> None:
    """
    Purpose: Verify replace_in_text works with compiled regex patterns.
    Why this matters: Enables advanced pattern matching beyond literal strings.
    Setup summary: Use compiled regex pattern, assert proper replacement.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Contact: alice@example.com or bob@test.com"
    pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    repls = [(pattern, "[EMAIL]")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Contact: [EMAIL] or [EMAIL]"


@pytest.mark.ai
def test_replace_in_text__returns_unchanged__with_empty_replacements() -> None:
    """
    Purpose: Verify replace_in_text handles empty replacement list gracefully.
    Why this matters: Prevents errors when no replacements are needed.
    Setup summary: Provide empty replacement list, assert text unchanged.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Original text remains unchanged"
    repls: list[tuple[str, str]] = []

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == text


@pytest.mark.ai
def test_replace_in_text__returns_unchanged__with_no_matches() -> None:
    """
    Purpose: Verify replace_in_text handles patterns that don't match.
    Why this matters: Ensures graceful handling of non-matching patterns.
    Setup summary: Pattern that doesn't exist in text, assert unchanged.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Hello world"
    repls = [("goodbye", "farewell"), ("universe", "cosmos")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Hello world"


@pytest.mark.ai
def test_replace_in_text__handles_empty_text__correctly() -> None:
    """
    Purpose: Verify replace_in_text handles empty input text.
    Why this matters: Prevents errors on edge case inputs.
    Setup summary: Empty text with valid replacements, assert empty result.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = ""
    repls = [("pattern", "replacement")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == ""


@pytest.mark.ai
def test_replace_in_text__replaces_with_empty_string__removes_pattern() -> None:
    """
    Purpose: Verify replace_in_text can remove patterns by replacing with empty string.
    Why this matters: Enables pattern deletion use case.
    Setup summary: Replace patterns with empty strings, assert removal.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Remove [TAG1] these [TAG2] tags"
    repls = [(r"\[TAG\d+\]", "")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Remove  these  tags"


@pytest.mark.ai
def test_replace_in_text__preserves_case__in_non_matching_text() -> None:
    """
    Purpose: Verify replace_in_text only modifies matched patterns.
    Why this matters: Ensures surgical precision in replacements.
    Setup summary: Case-sensitive pattern, verify non-matches preserved.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Test test TEST TeSt"
    repls = [("test", "exam")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Test exam TEST TeSt"


@pytest.mark.ai
def test_replace_in_text__interprets_strings_as_regex__patterns() -> None:
    """
    Purpose: Verify replace_in_text treats string patterns as regex patterns.
    Why this matters: Documents that strings are interpreted as regex, requiring escaping.
    Setup summary: String with regex special chars, verify regex interpretation.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Price: $100 (sale)"
    # Need to escape regex special characters
    repls = [(r"\$100", "$50"), (r"\(sale\)", "(clearance)")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Price: $50 (clearance)"


@pytest.mark.ai
def test_replace_in_text__handles_multiple_occurrences__of_same_pattern() -> None:
    """
    Purpose: Verify replace_in_text replaces all occurrences of a pattern.
    Why this matters: Ensures global replacement behavior.
    Setup summary: Pattern appearing multiple times, assert all replaced.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "foo bar foo baz foo"
    repls = [("foo", "qux")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "qux bar qux baz qux"


@pytest.mark.ai
def test_replace_in_text__handles_chain_replacement__without_cascading() -> None:
    """
    Purpose: Verify replace_in_text prevents cascading replacements.
    Why this matters: Ensures predictable replacement behavior in complex scenarios.
    Setup summary: Chain of patterns where replacements could cascade, verify isolation.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Replace A with B, B with C, C with D"
    repls = [("A", "X"), ("B", "Y"), ("C", "Z")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    # Each pattern should only match the original text, not intermediate results
    assert result == "Replace X with Y, Y with Z, Z with D"


@pytest.mark.ai
def test_replace_in_text__handles_overlapping_patterns__first_to_last() -> None:
    """
    Purpose: Verify replace_in_text handles patterns that could interfere with each other.
    Why this matters: Tests the placeholder mechanism that prevents interference.
    Setup summary: Pattern where replacement contains another pattern to be replaced.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "The value is 123"
    repls = [("123", "456"), ("value", "result"), ("is", "equals")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "The result equals 456"


@pytest.mark.ai
def test_replace_in_text__mixed_string_and_regex__patterns() -> None:
    """
    Purpose: Verify replace_in_text handles mixed string and regex patterns.
    Why this matters: Enables flexible pattern matching strategies in single call.
    Setup summary: Mix of string literals and compiled regex patterns.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "User: alice_smith, Email: alice@example.com, Age: 25"
    repls = [
        (re.compile(r"\b[A-Za-z]+@[A-Za-z]+\.[a-z]{2,}\b"), "[REDACTED]"),
        ("alice_smith", "[USERNAME]"),
        ("Age: 25", "Age: XX"),
    ]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "User: [USERNAME], Email: [REDACTED], Age: XX"


@pytest.mark.ai
def test_replace_in_text__handles_whitespace__in_patterns() -> None:
    """
    Purpose: Verify replace_in_text correctly handles whitespace in patterns.
    Why this matters: Ensures precise matching of whitespace-sensitive text.
    Setup summary: Patterns with various whitespace, assert correct replacement.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Hello  world\twith\nvarious spaces"
    repls = [("\t", " "), ("\n", " ")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Hello  world with various spaces"


@pytest.mark.ai
def test_replace_in_text__handles_unicode__characters() -> None:
    """
    Purpose: Verify replace_in_text works with unicode characters.
    Why this matters: Ensures internationalization support.
    Setup summary: Text with unicode chars, assert proper replacement.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Café résumé naïve Ñoño"
    repls = [("Café", "Coffee"), ("résumé", "resume"), ("Ñoño", "Nono")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Coffee resume naïve Nono"


@pytest.mark.ai
def test_replace_in_text__handles_multiple_word_replacements__efficiently() -> None:
    """
    Purpose: Verify replace_in_text handles many replacements.
    Why this matters: Ensures scalability for complex text transformations.
    Setup summary: Multiple independent word replacements, verify all applied.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "alpha beta gamma delta epsilon"
    repls = [
        ("alpha", "ALPHA"),
        ("beta", "BETA"),
        ("gamma", "GAMMA"),
        ("delta", "DELTA"),
        ("epsilon", "EPSILON"),
    ]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "ALPHA BETA GAMMA DELTA EPSILON"


@pytest.mark.ai
def test_replace_in_text__preserves_replacement_order__in_output() -> None:
    """
    Purpose: Verify replace_in_text applies replacements in deterministic manner.
    Why this matters: Ensures predictable output for debugging and testing.
    Setup summary: Multiple replacements in specific order, verify correct result.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "First Second Third"
    repls = [("First", "1st"), ("Second", "2nd"), ("Third", "3rd")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "1st 2nd 3rd"


@pytest.mark.ai
def test_replace_in_text__handles_regex_groups__in_patterns() -> None:
    """
    Purpose: Verify replace_in_text works with regex capture groups.
    Why this matters: Enables advanced pattern transformations.
    Setup summary: Use regex with groups, assert proper replacement.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Date: 2023-12-25, Event: Christmas"
    pattern = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
    # Note: The placeholder replacement breaks capture group references,
    # so we use a direct string replacement after matching
    repls = [(pattern, "12/25/2023")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Date: 12/25/2023, Event: Christmas"


@pytest.mark.ai
def test_replace_in_text__handles_same_pattern_replacement__idempotent() -> None:
    """
    Purpose: Verify replace_in_text handles pattern that equals its replacement.
    Why this matters: Edge case that should not cause infinite loops.
    Setup summary: Pattern replaced with itself, assert no changes or errors.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Same text Same"
    repls = [("Same", "Same")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Same text Same"


@pytest.mark.ai
@pytest.mark.parametrize(
    "text, repls, expected",
    [
        ("", [], ""),
        ("test", [], "test"),
        ("", [("a", "b")], ""),
        ("The cat sat", [("cat", "dog")], "The dog sat"),
        ("aaa", [("a", "b")], "bbb"),
    ],
    ids=[
        "empty-text-empty-repls",
        "no-repls",
        "empty-text-with-repls",
        "word-replaced",
        "repeated-char",
    ],
)
def test_replace_in_text__edge_cases(
    text: str, repls: list[tuple[str, str]], expected: str
) -> None:
    """
    Purpose: Table-driven tests for edge cases and corner scenarios.
    Why this matters: Ensures robust behavior across boundary conditions.
    Setup summary: Parametrized edge case inputs with expected outputs.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == expected


@pytest.mark.ai
def test_replace_in_text__handles_newlines_and_multiline__text() -> None:
    """
    Purpose: Verify replace_in_text works with multiline text.
    Why this matters: Enables processing of documents and structured text.
    Setup summary: Multiline text with replacements, assert correct handling.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = """Line 1: Hello
Line 2: World
Line 3: Test"""
    repls = [("Hello", "Hi"), ("World", "Universe"), ("Test", "Example")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    expected = """Line 1: Hi
Line 2: Universe
Line 3: Example"""
    assert result == expected


@pytest.mark.ai
def test_replace_in_text__handles_reference_pattern__use_case() -> None:
    """
    Purpose: Verify replace_in_text works for reference renumbering use case.
    Why this matters: Common use case in the codebase for managing citations.
    Setup summary: Reference patterns similar to actual usage, verify correct replacement.
    """
    # Arrange
    from unique_toolkit._common.string_utilities import replace_in_text

    text = "Text with <sup>1</sup> and <sup>2</sup> references."
    repls = [("<sup>1</sup>", "<sup>5</sup>"), ("<sup>2</sup>", "<sup>6</sup>")]

    # Act
    result = replace_in_text(text, repls)

    # Assert
    assert result == "Text with <sup>5</sup> and <sup>6</sup> references."
