"""
Unit tests for SubAgentReferencesPostprocessor in references.py.

Focus: regression coverage for the bug where existing references on the
loop response (e.g. those added by DisplayCodeInterpreterFilesPostProcessor)
were silently wiped out when SubAgentReferencesPostprocessor ran.
"""

import pytest

from unique_toolkit.agentic.tools.a2a.postprocessing.references import (
    _add_sub_agent_references_in_place,
)
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content import ContentReference
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse


@pytest.fixture
def existing_doc_reference() -> ContentReference:
    """A pre-existing ContentReference such as one added by a prior postprocessor."""
    return ContentReference(
        id="cont_existing_doc",
        message_id="msg_1",
        name="generated_chart.png",
        sequence_number=1,
        source_id="cont_existing_doc",
        source="node-ingestion-chunks",
        url="unique://content/cont_existing_doc",
    )


def _make_loop_response(
    text: str,
    references: list[ContentReference] | None,
) -> LanguageModelStreamResponse:
    return LanguageModelStreamResponse(
        message=ChatMessage(
            id="msg_1",
            chat_id="chat_1",
            role=ChatMessageRole.ASSISTANT,
            text=text,
            original_text=text,
            references=references,
        ),
    )


@pytest.mark.ai
def test_add_sub_agent_references_in_place__preserves_existing_refs__when_no_sub_agent_responses(
    existing_doc_reference: ContentReference,
) -> None:
    """
    Purpose: Verify pre-existing references on the loop response are not wiped
    when there are no sub-agent responses to merge in.
    Why this matters: A previous postprocessor (e.g. DisplayCodeInterpreterFilesPostProcessor)
    may have already populated message.references; this postprocessor must not overwrite
    them with an empty list, otherwise the user sees `<sup>1</sup>` in text with no chip.
    Setup summary: Loop response carrying one existing ref, empty sub-agent responses,
    assert the existing ref survives unchanged.
    """
    # Arrange
    loop_response = _make_loop_response(
        text="See <sup>1</sup> for the chart.",
        references=[existing_doc_reference],
    )

    # Act
    _add_sub_agent_references_in_place(loop_response=loop_response, responses=[])

    # Assert
    assert loop_response.message.references == [existing_doc_reference]


@pytest.mark.ai
def test_add_sub_agent_references_in_place__handles_none_references__without_error() -> (
    None
):
    """
    Purpose: Verify the function tolerates message.references being None.
    Why this matters: ChatMessage.references is Optional; the seeding step must coerce
    None to an empty list rather than crashing.
    Setup summary: Loop response with references=None and no sub-agent responses,
    assert references becomes an empty list.
    """
    # Arrange
    loop_response = _make_loop_response(text="No refs here.", references=None)

    # Act
    _add_sub_agent_references_in_place(loop_response=loop_response, responses=[])

    # Assert
    assert loop_response.message.references == []
