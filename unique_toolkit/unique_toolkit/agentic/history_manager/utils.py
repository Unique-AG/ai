import json
import logging
from copy import deepcopy
from typing import Any

from unique_toolkit.agentic.tools.schemas import Source
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelToolMessage,
)

logger = logging.getLogger(__name__)


def convert_tool_interactions_to_content_messages(
    loop_history: list[LanguageModelMessage],
) -> list[LanguageModelMessage]:
    new_loop_history = []
    copy_loop_history = deepcopy(loop_history)

    for message in copy_loop_history:
        if isinstance(message, LanguageModelAssistantMessage) and message.tool_calls:
            new_loop_history.append(_convert_tool_call_to_content(message))

        elif isinstance(message, LanguageModelToolMessage):
            new_loop_history.append(_convert_tool_call_response_to_content(message))
        else:
            new_loop_history.append(message)

    return new_loop_history


def _convert_tool_call_to_content(
    assistant_message: LanguageModelAssistantMessage,
) -> LanguageModelAssistantMessage:
    assert assistant_message.tool_calls is not None
    new_content = "The assistant requested the following tool_call:"
    for tool_call in assistant_message.tool_calls:
        new_content += (
            f"\n\n- {tool_call.function.name}: {tool_call.function.arguments}"
        )
    assistant_message.tool_calls = None
    assistant_message.content = new_content

    return assistant_message


def _convert_tool_call_response_to_content(
    tool_message: LanguageModelToolMessage,
) -> LanguageModelAssistantMessage:
    new_content = f"The assistant received the following tool_call_response: {tool_message.name}, {tool_message.content}"
    assistant_message = LanguageModelAssistantMessage(
        content=new_content,
    )
    return assistant_message


def transform_chunks_to_string(
    content_chunks: list[ContentChunk],
    max_source_number: int,
) -> tuple[str, list[dict[str, Any]]]:
    """Transform content chunks into a string of sources.

    Args:
        content_chunks (list[ContentChunk]): The content chunks to transform
        max_source_number (int): The maximum source number to use

    Returns:
        str: String for the tool call response
    """
    if not content_chunks:
        return "No relevant sources found.", []
    sources: list[dict[str, Any]] = [
        {
            "source_number": max_source_number + i,
            "content": chunk.text,
        }
        for i, chunk in enumerate(content_chunks)
    ]
    return json.dumps(sources), sources


def load_sources_from_string(
    source_string: str,
) -> list[Source] | None:
    """Transform JSON string from language model tool message in the tool call response into Source objects"""

    try:
        # First, try parsing as JSON (new format)
        sources_data = json.loads(source_string)
        return [Source.model_validate(source) for source in sources_data]
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse source string")
        return None
