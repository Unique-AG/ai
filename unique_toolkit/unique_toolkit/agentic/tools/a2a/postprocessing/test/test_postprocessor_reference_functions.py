from unique_toolkit.agentic.tools.a2a.postprocessing.postprocessor import (
    _replace_references_in_text,
    _replace_references_in_text_non_overlapping,
)


class TestReplaceReferencesInTextNonOverlapping:
    """Test cases for _replace_references_in_text_non_overlapping function."""

    def test_single_reference_replacement(self):
        """Test replacing a single reference."""
        text = "This is a test<sup>1</sup> with one reference."
        ref_map = {1: 5}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        expected = "This is a test<sup>5</sup> with one reference."
        assert result == expected

    def test_multiple_reference_replacements(self):
        """Test replacing multiple references."""
        text = "First<sup>1</sup> and second<sup>2</sup> and third<sup>3</sup>."
        ref_map = {1: 10, 2: 20, 3: 30}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        expected = "First<sup>10</sup> and second<sup>20</sup> and third<sup>30</sup>."
        assert result == expected

    def test_no_references_in_text(self):
        """Test with text that has no references."""
        text = "This text has no references at all."
        ref_map = {1: 5, 2: 10}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        assert result == text

    def test_empty_ref_map(self):
        """Test with empty reference map."""
        text = "This text has<sup>1</sup> references but empty map."
        ref_map = {}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        assert result == text

    def test_empty_text(self):
        """Test with empty text."""
        text = ""
        ref_map = {1: 5}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        assert result == ""

    def test_reference_not_in_map(self):
        """Test with references in text that are not in the map."""
        text = "Reference<sup>1</sup> and<sup>2</sup> and<sup>3</sup>."
        ref_map = {1: 10}  # Only maps reference 1
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        expected = "Reference<sup>10</sup> and<sup>2</sup> and<sup>3</sup>."
        assert result == expected

    def test_duplicate_references_in_text(self):
        """Test with duplicate references in text."""
        text = "First<sup>1</sup> and second<sup>1</sup> occurrence."
        ref_map = {1: 99}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        expected = "First<sup>99</sup> and second<sup>99</sup> occurrence."
        assert result == expected

    def test_adjacent_references(self):
        """Test with adjacent references."""
        text = "Adjacent<sup>1</sup><sup>2</sup> references."
        ref_map = {1: 10, 2: 20}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        expected = "Adjacent<sup>10</sup><sup>20</sup> references."
        assert result == expected

    def test_references_with_multi_digit_numbers(self):
        """Test with multi-digit reference numbers."""
        text = "Reference<sup>123</sup> and<sup>456</sup>."
        ref_map = {123: 789, 456: 101112}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        expected = "Reference<sup>789</sup> and<sup>101112</sup>."
        assert result == expected

    def test_references_at_text_boundaries(self):
        """Test with references at the beginning and end of text."""
        text = "<sup>1</sup>Start and end<sup>2</sup>"
        ref_map = {1: 100, 2: 200}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        expected = "<sup>100</sup>Start and end<sup>200</sup>"
        assert result == expected

    def test_malformed_references_ignored(self):
        """Test that malformed references are ignored."""
        text = "Good<sup>1</sup> and bad<sup>abc</sup> and<sup></sup>."
        ref_map = {1: 10}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        expected = "Good<sup>10</sup> and bad<sup>abc</sup> and<sup></sup>."
        assert result == expected

    def test_zero_reference_number(self):
        """Test with zero as reference number."""
        text = "Zero reference<sup>0</sup> here."
        ref_map = {0: 100}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        expected = "Zero reference<sup>100</sup> here."
        assert result == expected

    def test_negative_reference_numbers(self):
        """Test with negative reference numbers (edge case)."""
        text = "Negative<sup>-1</sup> reference."
        ref_map = {-1: 5}
        result = _replace_references_in_text_non_overlapping(text, ref_map)
        expected = "Negative<sup>5</sup> reference."
        assert result == expected


class TestReplaceReferencesInText:
    """Test cases for _replace_references_in_text function."""

    def test_non_overlapping_simple_case(self):
        """Test simple non-overlapping case."""
        text = "Reference<sup>1</sup> and<sup>2</sup>."
        ref_map = {1: 10, 2: 20}
        result = _replace_references_in_text(text, ref_map)
        expected = "Reference<sup>10</sup> and<sup>20</sup>."
        assert result == expected

    def test_overlapping_references_case1(self):
        """Test overlapping case where new reference numbers conflict with existing ones."""
        text = "First<sup>1</sup> and second<sup>2</sup>."
        ref_map = {1: 2, 2: 1}  # Swap references
        result = _replace_references_in_text(text, ref_map)
        expected = "First<sup>2</sup> and second<sup>1</sup>."
        assert result == expected

    def test_overlapping_references_case2(self):
        """Test overlapping case with chain of replacements."""
        text = "Refs<sup>1</sup><sup>2</sup><sup>3</sup>."
        ref_map = {1: 2, 2: 3, 3: 1}  # Circular replacement
        result = _replace_references_in_text(text, ref_map)
        expected = "Refs<sup>2</sup><sup>3</sup><sup>1</sup>."
        assert result == expected

    def test_overlapping_with_higher_numbers(self):
        """Test overlapping where replacement numbers are higher than originals."""
        text = "Test<sup>1</sup> and<sup>2</sup>."
        ref_map = {1: 3, 2: 1}  # 2 -> 1, but 1 -> 3
        result = _replace_references_in_text(text, ref_map)
        expected = "Test<sup>3</sup> and<sup>1</sup>."
        assert result == expected

    def test_complex_overlapping_scenario(self):
        """Test complex overlapping scenario with multiple conflicts."""
        text = "A<sup>1</sup>B<sup>2</sup>C<sup>3</sup>D<sup>4</sup>."
        ref_map = {1: 4, 2: 1, 3: 2, 4: 3}  # Full rotation
        result = _replace_references_in_text(text, ref_map)
        expected = "A<sup>4</sup>B<sup>1</sup>C<sup>2</sup>D<sup>3</sup>."
        assert result == expected

    def test_empty_ref_map(self):
        """Test with empty reference map."""
        text = "Text with<sup>1</sup> references."
        ref_map = {}
        result = _replace_references_in_text(text, ref_map)
        assert result == text

    def test_empty_text(self):
        """Test with empty text."""
        text = ""
        ref_map = {1: 2}
        result = _replace_references_in_text(text, ref_map)
        assert result == ""

    def test_no_references_in_text(self):
        """Test with text containing no references."""
        text = "This text has no references."
        ref_map = {1: 10, 2: 20}
        result = _replace_references_in_text(text, ref_map)
        assert result == text

    def test_single_reference_no_overlap(self):
        """Test single reference with no overlap potential."""
        text = "Single<sup>5</sup> reference."
        ref_map = {5: 100}
        result = _replace_references_in_text(text, ref_map)
        expected = "Single<sup>100</sup> reference."
        assert result == expected

    def test_partial_overlap(self):
        """Test case where only some references have overlapping numbers."""
        text = "Mix<sup>1</sup><sup>2</sup><sup>10</sup>."
        ref_map = {1: 2, 2: 20, 10: 100}  # Only 1->2 creates potential overlap
        result = _replace_references_in_text(text, ref_map)
        expected = "Mix<sup>2</sup><sup>20</sup><sup>100</sup>."
        assert result == expected

    def test_self_mapping(self):
        """Test case where a reference maps to itself."""
        text = "Self<sup>1</sup> and other<sup>2</sup>."
        ref_map = {1: 1, 2: 10}  # 1 maps to itself
        result = _replace_references_in_text(text, ref_map)
        expected = "Self<sup>1</sup> and other<sup>10</sup>."
        assert result == expected

    def test_duplicate_references_with_overlap(self):
        """Test duplicate references in text with overlapping mappings."""
        text = "Dup<sup>1</sup> and dup<sup>1</sup> and<sup>2</sup>."
        ref_map = {1: 2, 2: 1}  # Swap
        result = _replace_references_in_text(text, ref_map)
        expected = "Dup<sup>2</sup> and dup<sup>2</sup> and<sup>1</sup>."
        assert result == expected

    def test_large_reference_numbers(self):
        """Test with large reference numbers."""
        text = "Large<sup>999</sup> and<sup>1000</sup>."
        ref_map = {999: 1000, 1000: 999}  # Swap large numbers
        result = _replace_references_in_text(text, ref_map)
        expected = "Large<sup>1000</sup> and<sup>999</sup>."
        assert result == expected

    def test_zero_and_negative_with_overlap(self):
        """Test zero and negative numbers with potential overlap."""
        text = "Zero<sup>0</sup> and neg<sup>-1</sup> and pos<sup>1</sup>."
        ref_map = {0: 1, -1: 0, 1: -1}  # Circular with zero and negative
        result = _replace_references_in_text(text, ref_map)
        expected = "Zero<sup>1</sup> and neg<sup>0</sup> and pos<sup>-1</sup>."
        assert result == expected

    def test_max_ref_calculation_edge_case(self):
        """Test edge case for max_ref calculation with empty map."""
        text = "Some<sup>1</sup> text."
        ref_map = {}
        result = _replace_references_in_text(text, ref_map)
        assert result == text

    def test_phase_separation_correctness(self):
        """Test that the two-phase approach correctly handles complex overlaps."""
        # This test ensures the intermediate unique references don't interfere
        text = "Test<sup>1</sup><sup>2</sup><sup>3</sup><sup>4</sup><sup>5</sup>."
        ref_map = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}  # Reverse order
        result = _replace_references_in_text(text, ref_map)
        expected = "Test<sup>5</sup><sup>4</sup><sup>3</sup><sup>2</sup><sup>1</sup>."
        assert result == expected

    def test_intermediate_collision_avoidance(self):
        """Test that intermediate unique references don't collide with existing text."""
        # Create a scenario where intermediate refs might collide
        text = "Refs<sup>1</sup><sup>2</sup> and existing<sup>6</sup><sup>7</sup>."
        ref_map = {1: 2, 2: 1}  # Simple swap
        result = _replace_references_in_text(text, ref_map)
        expected = "Refs<sup>2</sup><sup>1</sup> and existing<sup>6</sup><sup>7</sup>."
        assert result == expected
        # The existing <sup>6</sup> and <sup>7</sup> should remain unchanged
