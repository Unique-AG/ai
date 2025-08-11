import json
import re

from pydantic import BaseModel
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.schemas import (
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelToolMessage,
)
from unique_toolkit.unique_toolkit.base_agents.loop_agent.schemas import AgentChunksHandler


SUGGESTED_FOLLOW_UP_QUESTIONS_PATTERN = (
    r"\n\n---\n\n_Suggested follow-up questions:_\n\n.*"
)


class SourceReductionResult(BaseModel):
    message: LanguageModelToolMessage
    reduced_chunks: list[ContentChunk]
    chunks_handler: AgentChunksHandler
    chunk_offset: int
    source_offset: int

    class Config:
        arbitrary_types_allowed = True


def remove_ticker_plot_data_from_history(
    history: list[LanguageModelMessage],
) -> list[LanguageModelMessage]:
    """
    Remove the plot data from the history.
    """
    raise NotImplementedError(
        "this function can not statically import the Plot stuff it must be generalized"
    )

    # for message in history:
    #     if isinstance(message.content, str):
    #         for plotting_backend in (
    #             PlotlyPlottingBackend,
    #             NextPlottingBackend,
    #         ):
    #             message.content = plotting_backend.remove_result_from_text(
    #                 message.content
    #             )
    # return history


def remove_suggested_questions_from_history(
    history: list[LanguageModelMessage],
) -> list[LanguageModelMessage]:
    """
    Remove the suggested questions from messages in the history. Suggested questions are separated from the main message by a pattern.
    """
    for message in history:
        if isinstance(message.content, str):
            message.content = re.sub(
                SUGGESTED_FOLLOW_UP_QUESTIONS_PATTERN,
                "",
                message.content,
                flags=re.DOTALL,
            )
    return history


def reduce_message_length_by_reducing_sources_in_tool_response(
    history: list[LanguageModelMessage],
    chunks_handler: AgentChunksHandler,
) -> tuple[list[LanguageModelMessage], AgentChunksHandler]:
    """
    Reduce the message length by removing the last source result of each tool call.
    If there is only one source for a tool call, the tool call message is returned unchanged.
    """
    history_reduced: list[LanguageModelMessage] = []
    content_chunks_reduced: list[ContentChunk] = []
    chunk_offset = 0
    source_offset = 0

    for message in history:
        if _should_reduce_message(message):
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


def _should_reduce_message(message: LanguageModelMessage) -> bool:
    """Determine if a message should have its sources reduced."""
    raise NotImplementedError(
        "This function can not statically import the ReadContentTool, it must be generalized"
    )
    # return (
    #     message.role == LanguageModelMessageRole.TOOL
    #     and isinstance(message, LanguageModelToolMessage)
    #     and message.name != ReadContentTool.name
    # )


def _reduce_sources_in_tool_message(
    message: LanguageModelToolMessage,
    chunks_handler: AgentChunksHandler,
    chunk_offset: int,
    source_offset: int,
) -> SourceReductionResult:
    """
    Reduce the sources in the tool message by removing the last source.
    If there is only one source, the message is returned unchanged.
    """
    tool_chunks = chunks_handler.tool_chunks[message.tool_call_id]["chunks"]
    num_sources = len(tool_chunks)

    if num_sources == 0:
        return SourceReductionResult(
            message=message,
            reduced_chunks=[],
            chunks_handler=chunks_handler,
            chunk_offset=chunk_offset,
            source_offset=source_offset,
        )

    # Reduce chunks, keeping all but the last one if multiple exist
    if num_sources == 1:
        reduced_chunks = tool_chunks
        content_chunks_reduced = chunks_handler.chunks[
            chunk_offset : chunk_offset + num_sources
        ]
    else:
        reduced_chunks = tool_chunks[:-1]
        content_chunks_reduced = chunks_handler.chunks[
            chunk_offset : chunk_offset + num_sources - 1
        ]
        chunks_handler.tool_chunks[message.tool_call_id]["chunks"] = (
            reduced_chunks
        )

    # Create new message with reduced sources
    new_message = _create_tool_call_message_with_reduced_sources(
        message=message,
        content_chunks=reduced_chunks,
        source_offset=source_offset,
    )

    return SourceReductionResult(
        message=new_message,
        reduced_chunks=content_chunks_reduced,
        chunks_handler=chunks_handler,
        chunk_offset=chunk_offset + num_sources,
        source_offset=source_offset
        + num_sources
        - (1 if num_sources != 1 else 0),
    )


def _create_tool_call_message_with_reduced_sources(
    message: LanguageModelToolMessage,
    content_chunks: list[ContentChunk] | None = None,
    source_offset: int = 0,
) -> LanguageModelToolMessage:
    # Handle special case for TableSearch tool
    if message.name == "TableSearch":
        return _create_reduced_table_search_message(
            message, content_chunks, source_offset
        )

    # Handle empty content case
    if not content_chunks:
        return _create_reduced_empty_sources_message(message)

    # Handle standard content chunks
    return _create_reduced_standard_sources_message(
        message, content_chunks, source_offset
    )


def _create_reduced_table_search_message(
    message: LanguageModelToolMessage,
    content_chunks: list[ContentChunk] | None,
    source_offset: int,
) -> LanguageModelToolMessage:
    """
    Create a message for TableSearch tool.

    Note: TableSearch content consists of a single result with SQL results,
    not content chunks.
    """
    if not content_chunks:
        content = message.content
    else:
        if isinstance(message.content, str):
            content_dict = json.loads(message.content)
        elif isinstance(message.content, dict):
            content_dict = message.content
        else:
            raise ValueError(
                f"Unexpected content type: {type(message.content)}"
            )

        content = json.dumps(
            {
                "source_number": source_offset,
                "content": content_dict.get("content"),
            }
        )

    return LanguageModelToolMessage(
        content=content,
        tool_call_id=message.tool_call_id,
        name=message.name,
    )


def _create_reduced_empty_sources_message(
    message: LanguageModelToolMessage,
) -> LanguageModelToolMessage:
    """Create a message when no content chunks are available."""
    return LanguageModelToolMessage(
        content="No relevant sources found.",
        tool_call_id=message.tool_call_id,
        name=message.name,
    )


def _create_reduced_standard_sources_message(
    message: LanguageModelToolMessage,
    content_chunks: list[ContentChunk],
    source_offset: int,
) -> LanguageModelToolMessage:
    """Create a message with standard content chunks."""
    sources = [
        {
            "source_number": source_offset + i,
            "content": chunk.text,
        }
        for i, chunk in enumerate(content_chunks)
    ]

    return LanguageModelToolMessage(
        content=str(sources),
        tool_call_id=message.tool_call_id,
        name=message.name,
    )
