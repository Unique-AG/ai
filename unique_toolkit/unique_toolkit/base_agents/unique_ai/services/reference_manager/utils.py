import logging
import re

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model import LanguageModelMessageRole
from unique_toolkit.language_model.schemas import (
    LanguageModelMessage,
    LanguageModelToolMessage,
)

from _common.agents.loop_agent.utils.history_manipulation import (
    _reduce_sources_in_tool_message,
)
from unique_toolkit.unique_toolkit.tools.agent_chunks_handler import AgentChunksHandler

logger = logging.getLogger(__name__)


# Pattern for matching numbers in sup tags
SUP_PATTERN = re.compile(r"<sup>(\d+)</sup>")


def update_reference_numbers(
    message: str,
    mapping: dict[int, int],
    pattern: re.Pattern = SUP_PATTERN,
) -> str:
    """
    Update reference numbers in a message based on a mapping of old to new numbers.
    Converts <sup>number</sup> format to [source<number>] format.

    Args:
        message: The message to update
        mapping: Dictionary mapping old reference numbers to new ones
        pattern: Regular expression pattern to use for matching (should be SUP_PATTERN)

    Returns:
        The updated message with new reference numbers in [source<number>] format
    """

    def replace_match(match):
        # Extract the reference number from the match
        ref_num = int(match.group(1))

        if ref_num in mapping:
            # Convert from <sup>old_number</sup> to [source<new_number>]
            new_number = mapping[ref_num]
            return f"[source{new_number}]"

        # If no mapping exists, return the original match
        return match.group(0)

    return pattern.sub(replace_match, message)


def reduce_message_length_by_reducing_sources_in_tool_response_excluding_reference_manger_sources(
    history: list[LanguageModelMessage],
    chunks_handler: AgentChunksHandler,
    source_offset: int,
    protected_tool_call_ids: set[str] = set(),
) -> tuple[list[LanguageModelMessage], AgentChunksHandler]:
    """
    Reduce the message length by removing the last source result of each tool call.
    If there is only one source for a tool call, the tool call message is returned unchanged.
    """
    history_reduced: list[LanguageModelMessage] = []
    content_chunks_reduced: list[ContentChunk] = []
    chunk_offset = 0

    # Keep the sources introduced by the handler
    content_chunks_reduced.extend(chunks_handler.chunks[:source_offset])

    for message in history:
        if (
            message.role == LanguageModelMessageRole.TOOL
            and isinstance(message, LanguageModelToolMessage)
            and message.tool_call_id not in protected_tool_call_ids
        ):
            result = _reduce_sources_in_tool_message(
                message,  # type: ignore
                chunks_handler,
                chunk_offset,
                source_offset,
            )
            content_chunks_reduced.extend(result.reduced_chunks)
            history_reduced.append(result.message)
            chunk_offset = result.chunk_offset
            source_offset = result.source_offset
        else:
            history_reduced.append(message)

    chunks_handler.replace(chunks=content_chunks_reduced)
    return history_reduced, chunks_handler
