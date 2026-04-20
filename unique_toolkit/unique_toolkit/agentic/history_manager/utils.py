import json
import logging
from copy import deepcopy
from typing import Any

from unique_toolkit.agentic.feature_flags import feature_flags
from unique_toolkit.agentic.tools.schemas import Source
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelToolMessage,
)

logger = logging.getLogger(__name__)


def get_selected_uploaded_content_ids(event: ChatEvent) -> set[str] | None:
    """Derive the set of content IDs the user explicitly selected.

    Returns ``None`` when the feature flag is disabled (meaning *all*
    uploaded images should be included), or a ``set[str]`` of IDs when
    only a subset should be attached.
    """
    if not feature_flags.enable_selected_uploaded_files_un_18215.is_enabled(
        event.company_id
    ):
        return None

    if not (
        hasattr(event.payload, "additional_parameters")
        and event.payload.additional_parameters
    ):
        return None

    return set(event.payload.additional_parameters.selected_uploaded_file_ids)


def serialize_tool_content_json(value: Any) -> str:
    """Serialize tool-role JSON text while preserving readable Unicode."""
    return json.dumps(value, ensure_ascii=False)


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
            "content_id": chunk.id,
            "content": chunk.text,
        }
        for i, chunk in enumerate(content_chunks)
    ]
    return serialize_tool_content_json(sources), sources


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


def _parse_sources_from_response(content: str) -> list[dict[str, Any]]:
    """Parse the JSON source array from a persisted tool response content string.

    Returns an empty list when the content is not valid JSON or not a list.
    """
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning(
            "_parse_sources_from_response: JSON parse failed (content_len=%d): %s",
            len(content),
            exc,
        )
        return []


def compute_max_source_number_from_tool_calls(
    tool_calls: list[Any],
) -> int:
    """Find the highest ``source_number`` across all persisted tool-call responses.

    Returns ``-1`` when no source numbers are found.
    """
    from unique_toolkit.chat.schemas import ChatMessageTool

    max_num = -1
    for tc in tool_calls:
        if not isinstance(tc, ChatMessageTool):
            continue
        if not tc.response or not tc.response.content:
            continue
        for entry in _parse_sources_from_response(tc.response.content):
            sn = entry.get("source_number")
            if isinstance(sn, int) and sn > max_num:
                max_num = sn
    return max_num


def build_source_map_from_tool_calls(
    tool_calls: list[Any],
) -> dict[int, ContentChunk]:
    """Build a mapping ``{source_number: ContentChunk}`` from persisted tool responses.

    Only entries that have both a valid ``source_number`` and ``content`` are included.
    """
    from unique_toolkit.chat.schemas import ChatMessageTool

    source_map: dict[int, ContentChunk] = {}
    for tc in tool_calls:
        if not isinstance(tc, ChatMessageTool):
            continue
        if not tc.response or not tc.response.content:
            continue
        for entry in _parse_sources_from_response(tc.response.content):
            sn = entry.get("source_number")
            text = entry.get("content")
            if isinstance(sn, int) and isinstance(text, str):
                content_id = entry.get("content_id") or ""
                source_map[sn] = ContentChunk(
                    id=content_id, text=text, key="", chunk_id=""
                )
    return source_map
