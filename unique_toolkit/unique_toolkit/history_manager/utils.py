import json
import logging
from copy import deepcopy

from unique_toolkit.content.schemas import ContentChunk, ContentMetadata
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelToolMessage,
)
from unique_toolkit.tools.schemas import Source
from unique_toolkit.tools.utils.source_handling.schema import (
    SourceFormatConfig,
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
    cfg: SourceFormatConfig | None,
    full_sources_serialize_dump: bool = False,
) -> tuple[str, list[Source]]:
    """Transform content chunks into a string of sources.

    Args:
        content_chunks (list[ContentChunk]): The content chunks to transform
        max_source_number (int): The maximum source number to use
        feature_full_sources (bool, optional): Whether to include the full source object. Defaults to False which is the old format.

    Returns:
        str: String for the tool call response
    """
    if not content_chunks:
        return "No relevant sources found.", []
    if full_sources_serialize_dump:
        sources = [
            Source(
                source_number=max_source_number + i,
                key=chunk.key,
                id=chunk.id,
                order=chunk.order,
                content=chunk.text,
                chunk_id=chunk.chunk_id,
                metadata=(
                    _format_metadata(chunk.metadata, cfg) or None
                    if chunk.metadata
                    else None
                ),
                url=chunk.url,
            ).model_dump(
                exclude_none=True,
                exclude_defaults=True,
                by_alias=True,
            )
            for i, chunk in enumerate(content_chunks)
        ]
    else:
        sources = [
            {
                "source_number": max_source_number + i,
                "content": chunk.text,
                **(
                    {"metadata": meta}
                    if (
                        meta := _format_metadata(chunk.metadata, cfg)
                    )  # only add when not empty
                    else {}
                ),
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


def _format_metadata(
    metadata: ContentMetadata | None,
    cfg: SourceFormatConfig | None,
) -> str:
    """
    Build the concatenated tag string from the chunk's metadata
    and the templates found in cfg.sections.
    Example result:
      "<|topic|>GenAI<|/topic|>\n<|date|>This document is from: 2025-04-29<|/date|>\n"
    """
    if metadata is None:
        return ""

    if cfg is None or not cfg.sections:
        # If no configuration is provided, return empty string
        return ""

    meta_dict = metadata.model_dump(exclude_none=True, by_alias=True)
    sections = cfg.sections

    parts: list[str] = []
    for key, template in sections.items():
        if key in meta_dict:
            parts.append(template.format(meta_dict[key]))

    return "".join(parts)


### In case we do not want any formatting of metadata we could use this function
# def _filtered_metadata(
#     meta: ContentMetadata | None,
#     cfg: SourceFormatConfig,
# ) -> dict[str, str] | None:
#     if meta is None:
#         return None

#     allowed = set(cfg.sections)
#     raw = meta.model_dump(exclude_none=True, by_alias=True)
#     pruned = {k: v for k, v in raw.items() if k in allowed}
#     return pruned or None
