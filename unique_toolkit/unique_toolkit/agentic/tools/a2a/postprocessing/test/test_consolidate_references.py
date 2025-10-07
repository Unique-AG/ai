from unittest.mock import MagicMock, patch

import pytest

from unique_toolkit.agentic.tools.a2a.postprocessing.postprocessor import (
    _consolidate_references_in_place,
)


class TestConsolidateReferencesInPlace:
    """Test cases for _consolidate_references_in_place function."""

    def _create_mock_loop_response(self, text: str = "Test response") -> MagicMock:
        """Create a mock LanguageModelStreamResponse object."""
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.text = text
        mock_response.message = mock_message
        return mock_response

    def test_empty_messages_list(self):
        """Test with empty messages list."""
        messages = []
        existing_refs = {}
        loop_response = self._create_mock_loop_response()

        _consolidate_references_in_place(messages, existing_refs, loop_response)

        assert existing_refs == {}

    def test_empty_existing_refs(self):
        """Test with empty existing references."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Test text with reference <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "source1",
                                "sequenceNumber": 1,
                                "name": "Test Source",
                                "url": "http://test.com",
                                "source": "test",
                                "originalIndex": [],
                            }
                        ],
                    }
                },
            }
        ]
        existing_refs = {}
        loop_response = self._create_mock_loop_response()

        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # Should start from index 1 since existing_refs is empty
        assert existing_refs == {"source1": 1}
        assert messages[0]["responses"][1]["references"][0]["sequenceNumber"] == 1
        assert (
            messages[0]["responses"][1]["text"]
            == "Test text with reference <sup>1</sup>"
        )

    def test_with_existing_refs(self):
        """Test with existing references."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "New text with reference <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "new_source",
                                "sequenceNumber": 1,
                                "name": "New Source",
                                "url": "http://new.com",
                                "source": "new",
                                "originalIndex": [],
                            }
                        ],
                    }
                },
            }
        ]
        existing_refs = {"existing_source": 5}
        loop_response = self._create_mock_loop_response()

        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # Should start from 6 (max existing + 1)
        assert existing_refs == {"existing_source": 5, "new_source": 6}
        assert messages[0]["responses"][1]["references"][0]["sequenceNumber"] == 6
        assert (
            messages[0]["responses"][1]["text"]
            == "New text with reference <sup>6</sup>"
        )

    def test_duplicate_source_ids(self):
        """Test with duplicate source IDs across different messages."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "First reference <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "shared_source",
                                "sequenceNumber": 1,
                                "name": "Shared Source",
                                "url": "http://shared.com",
                                "source": "shared",
                                "originalIndex": [],
                            }
                        ],
                    },
                    2: {
                        "text": "Second reference <sup>2</sup>",
                        "references": [
                            {
                                "sourceId": "shared_source",
                                "sequenceNumber": 2,
                                "name": "Shared Source",
                                "url": "http://shared.com",
                                "source": "shared",
                                "originalIndex": [],
                            }
                        ],
                    },
                },
            }
        ]
        existing_refs = {}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # Both should map to the same consolidated reference number
        assert existing_refs == {"shared_source": 1}
        assert messages[0]["responses"][1]["references"][0]["sequenceNumber"] == 1
        assert (
            messages[0]["responses"][2]["references"] == []
        )  # Should be empty for duplicate
        assert messages[0]["responses"][1]["text"] == "First reference <sup>1</sup>"
        assert messages[0]["responses"][2]["text"] == "Second reference <sup>1</sup>"

    def test_multiple_references_in_single_message(self):
        """Test with multiple references in a single message."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Text with <sup>1</sup> and <sup>2</sup> references",
                        "references": [
                            {
                                "sourceId": "source1",
                                "sequenceNumber": 1,
                                "name": "Source 1",
                                "url": "http://source1.com",
                                "source": "src1",
                                "originalIndex": [],
                            },
                            {
                                "sourceId": "source2",
                                "sequenceNumber": 2,
                                "name": "Source 2",
                                "url": "http://source2.com",
                                "source": "src2",
                                "originalIndex": [],
                            },
                        ],
                    }
                },
            }
        ]
        existing_refs = {}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        assert existing_refs == {"source1": 1, "source2": 2}
        # Both references should be in the message since they're unique
        assert len(messages[0]["responses"][1]["references"]) == 2
        assert (
            messages[0]["responses"][1]["text"]
            == "Text with <sup>1</sup> and <sup>2</sup> references"
        )

    def test_references_sorted_by_sequence_number(self):
        """Test that references are sorted by sequence number before processing."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Text with <sup>3</sup> and <sup>1</sup> and <sup>2</sup>",
                        "references": [
                            {
                                "sourceId": "source3",
                                "sequenceNumber": 3,
                                "name": "Source 3",
                                "url": "http://source3.com",
                                "source": "src3",
                                "originalIndex": [],
                            },
                            {
                                "sourceId": "source1",
                                "sequenceNumber": 1,
                                "name": "Source 1",
                                "url": "http://source1.com",
                                "source": "src1",
                                "originalIndex": [],
                            },
                            {
                                "sourceId": "source2",
                                "sequenceNumber": 2,
                                "name": "Source 2",
                                "url": "http://source2.com",
                                "source": "src2",
                                "originalIndex": [],
                            },
                        ],
                    }
                },
            }
        ]
        existing_refs = {}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # Should be processed in order 1, 2, 3 and assigned consecutive numbers
        assert existing_refs == {"source1": 1, "source2": 2, "source3": 3}
        assert (
            messages[0]["responses"][1]["text"]
            == "Text with <sup>3</sup> and <sup>1</sup> and <sup>2</sup>"
        )

    def test_empty_references_list(self):
        """Test with empty references list."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {1: {"text": "Text with no references", "references": []}},
            }
        ]
        existing_refs = {}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        assert existing_refs == {}
        assert messages[0]["responses"][1]["text"] == "Text with no references"

    def test_multiple_assistants(self):
        """Test with multiple assistants."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Assistant 1 text <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "source1",
                                "sequenceNumber": 1,
                                "name": "Source 1",
                                "url": "http://source1.com",
                                "source": "src1",
                                "originalIndex": [],
                            }
                        ],
                    }
                },
            },
            {
                "name": "Assistant2",
                "display_name": "Assistant2",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Assistant 2 text <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "source2",
                                "sequenceNumber": 1,
                                "name": "Source 2",
                                "url": "http://source2.com",
                                "source": "src2",
                                "originalIndex": [],
                            }
                        ],
                    }
                },
            },
        ]
        existing_refs = {}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        assert existing_refs == {"source1": 1, "source2": 2}
        assert messages[0]["responses"][1]["text"] == "Assistant 1 text <sup>1</sup>"
        assert messages[1]["responses"][1]["text"] == "Assistant 2 text <sup>2</sup>"

    def test_complex_reference_mapping(self):
        """Test complex scenario with overlapping sequence numbers and mixed source IDs."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Text with <sup>2</sup> and <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "sourceA",
                                "sequenceNumber": 2,
                                "name": "Source A",
                                "url": "http://sourceA.com",
                                "source": "srcA",
                                "originalIndex": [],
                            },
                            {
                                "sourceId": "sourceB",
                                "sequenceNumber": 1,
                                "name": "Source B",
                                "url": "http://sourceB.com",
                                "source": "srcB",
                                "originalIndex": [],
                            },
                        ],
                    },
                    2: {
                        "text": "Another text with <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "sourceA",  # Same source as above
                                "sequenceNumber": 1,
                                "name": "Source A",
                                "url": "http://sourceA.com",
                                "source": "srcA",
                                "originalIndex": [],
                            }
                        ],
                    },
                },
            }
        ]
        existing_refs = {"existing": 10}  # Start from 11

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # sourceB gets 11 (first in sorted order), sourceA gets 12
        assert existing_refs == {"existing": 10, "sourceB": 11, "sourceA": 12}

        # First message should have both references updated
        assert (
            messages[0]["responses"][1]["text"]
            == "Text with <sup>12</sup> and <sup>11</sup>"
        )
        assert len(messages[0]["responses"][1]["references"]) == 2

        # Second message should have empty references (duplicate sourceA) but updated text
        assert messages[0]["responses"][2]["text"] == "Another text with <sup>12</sup>"
        assert messages[0]["responses"][2]["references"] == []

    @patch(
        "unique_toolkit.agentic.tools.a2a.postprocessing.postprocessor._replace_references_in_text"
    )
    def test_replace_references_called_correctly(self, mock_replace):
        """Test that _replace_references_in_text is called with correct parameters."""
        mock_replace.return_value = "Updated text"

        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Original text <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "source1",
                                "sequenceNumber": 1,
                                "name": "Source 1",
                                "url": "http://source1.com",
                                "source": "src1",
                                "originalIndex": [],
                            }
                        ],
                    }
                },
            }
        ]
        existing_refs = {}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # Should call _replace_references_in_text with the original text and ref mapping
        mock_replace.assert_called_once_with("Original text <sup>1</sup>", {1: 1})
        assert messages[0]["responses"][1]["text"] == "Updated text"

    def test_reference_sequence_number_modification(self):
        """Test that reference sequence numbers are correctly modified in place."""
        original_ref = {
            "sourceId": "source1",
            "sequenceNumber": 5,
            "name": "Source 1",
            "url": "http://source1.com",
            "source": "src1",
            "originalIndex": [],
        }

        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {"text": "Text <sup>5</sup>", "references": [original_ref]}
                },
            }
        ]
        existing_refs = {}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # The original reference object should be modified in place
        assert original_ref["sequenceNumber"] == 1
        assert messages[0]["responses"][1]["references"][0]["sequenceNumber"] == 1

    @pytest.mark.parametrize(
        "existing_refs,expected_start",
        [
            ({}, 1),  # Empty -> start from 1
            ({"a": 1}, 2),  # Max 1 -> start from 2
            ({"a": 5, "b": 3, "c": 10}, 11),  # Max 10 -> start from 11
            ({"a": 0}, 1),  # Max 0 -> start from 1
        ],
    )
    def test_start_index_calculation(self, existing_refs, expected_start):
        """Test that start_index is calculated correctly from existing_refs."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Text <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "new_source",
                                "sequenceNumber": 1,
                                "name": "New Source",
                                "url": "http://new.com",
                                "source": "new",
                                "originalIndex": [],
                            }
                        ],
                    }
                },
            }
        ]

        existing_refs_copy = existing_refs.copy()
        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs_copy, loop_response)  # type: ignore

        assert existing_refs_copy["new_source"] == expected_start

    def test_no_responses_in_assistant(self):
        """Test with assistant that has no responses."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {},
            }
        ]
        existing_refs = {}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        assert existing_refs == {}

    def test_mixed_valid_and_invalid_messages(self):
        """Test with mix of valid messages and messages with no references."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Valid text <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "source1",
                                "sequenceNumber": 1,
                                "name": "Source 1",
                                "url": "http://source1.com",
                                "source": "src1",
                                "originalIndex": [],
                            }
                        ],
                    },
                    2: {"text": "No references", "references": []},
                    3: {
                        "text": "Another valid <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "source3",
                                "sequenceNumber": 1,
                                "name": "Source 3",
                                "url": "http://source3.com",
                                "source": "src3",
                                "originalIndex": [],
                            }
                        ],
                    },
                },
            }
        ]
        existing_refs = {}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # Only valid messages should be processed
        assert existing_refs == {"source1": 1, "source3": 2}
        assert messages[0]["responses"][1]["text"] == "Valid text <sup>1</sup>"
        assert messages[0]["responses"][2]["text"] == "No references"
        assert messages[0]["responses"][3]["text"] == "Another valid <sup>2</sup>"

    def test_sequence_number_sorting_within_responses(self):
        """Test that responses are processed in sorted sequence number order."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    3: {
                        "text": "Third message <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "source3",
                                "sequenceNumber": 1,
                                "name": "Source 3",
                                "url": "http://source3.com",
                                "source": "src3",
                                "originalIndex": [],
                            }
                        ],
                    },
                    1: {
                        "text": "First message <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "source1",
                                "sequenceNumber": 1,
                                "name": "Source 1",
                                "url": "http://source1.com",
                                "source": "src1",
                                "originalIndex": [],
                            }
                        ],
                    },
                    2: {
                        "text": "Second message <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "source2",
                                "sequenceNumber": 1,
                                "name": "Source 2",
                                "url": "http://source2.com",
                                "source": "src2",
                                "originalIndex": [],
                            }
                        ],
                    },
                },
            }
        ]
        existing_refs = {}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # Should be processed in order 1, 2, 3 based on response sequence numbers
        assert existing_refs == {"source1": 1, "source2": 2, "source3": 3}
        assert messages[0]["responses"][1]["text"] == "First message <sup>1</sup>"
        assert messages[0]["responses"][2]["text"] == "Second message <sup>2</sup>"
        assert messages[0]["responses"][3]["text"] == "Third message <sup>3</sup>"

    def test_source_id_already_exists_in_existing_refs(self):
        """Test when source ID already exists in existing_refs."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Message <sup>1</sup> with existing source",
                        "references": [
                            {
                                "sourceId": "existing_source",
                                "sequenceNumber": 1,
                                "name": "Existing Source",
                                "url": "http://existing.com",
                                "source": "existing",
                                "originalIndex": [],
                            }
                        ],
                    }
                },
            }
        ]
        existing_refs = {"existing_source": 99}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # Should use existing reference number and not add to new refs
        assert existing_refs == {"existing_source": 99}
        assert (
            messages[0]["responses"][1]["text"]
            == "Message <sup>99</sup> with existing source"
        )
        assert (
            messages[0]["responses"][1]["references"] == []
        )  # Should be empty since it's not new

    def test_edge_case_zero_and_negative_existing_refs(self):
        """Test edge case with zero and negative values in existing_refs."""
        messages = [
            {
                "name": "Assistant1",
                "display_name": "Assistant1",
                "display_config": {"mode": "expanded"},
                "responses": {
                    1: {
                        "text": "Text <sup>1</sup>",
                        "references": [
                            {
                                "sourceId": "new_source",
                                "sequenceNumber": 1,
                                "name": "New Source",
                                "url": "http://new.com",
                                "source": "new",
                                "originalIndex": [],
                            }
                        ],
                    }
                },
            }
        ]
        existing_refs = {"zero": 0, "negative": -5, "positive": 3}

        loop_response = self._create_mock_loop_response()
        _consolidate_references_in_place(messages, existing_refs, loop_response)  # type: ignore

        # Should start from max(0, -5, 3) + 1 = 4
        assert existing_refs["new_source"] == 4
