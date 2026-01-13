from typing import Any, Required, Sequence

from openai.types.responses import (
    ResponseIncludable,
    ResponseInputItemParam,
    ResponseOutputItem,
    ResponseTextConfigParam,
    ToolParam,
    response_create_params,
)
from openai.types.shared_params import Metadata, Reasoning
from typing_extensions import TypedDict

from unique_toolkit import LanguageModelToolDescription
from unique_toolkit.agentic.loop_runner.base import _ResponsesLoopIterationRunnerKwargs
from unique_toolkit.chat.service import LanguageModelMessages
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageOptions,
    ResponsesLanguageModelStreamResponse,
)


class _ResponsesStreamingHandlerKwargs(TypedDict, total=False):
    messages: Required[
        str
        | LanguageModelMessages
        | Sequence[
            ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
        ]
    ]
    model_name: Required[str]
    tools: Sequence[LanguageModelToolDescription | ToolParam]
    content_chunks: list[ContentChunk]
    start_text: str
    debug_info: dict[str, Any]
    temperature: float
    include: list[ResponseIncludable]
    instructions: str
    max_output_tokens: int
    metadata: Metadata
    parallel_tool_calls: bool
    text: ResponseTextConfigParam
    tool_choice: response_create_params.ToolChoice
    top_p: float
    reasoning: Reasoning
    other_options: dict[str, Any]


def _extract_responses_streaming_kwargs(
    kwargs: _ResponsesLoopIterationRunnerKwargs,
) -> _ResponsesStreamingHandlerKwargs:
    res = _ResponsesStreamingHandlerKwargs(
        messages=kwargs["messages"],
        model_name=kwargs["model"].name,
    )

    for k in [
        "tools",
        "content_chunks",
        "start_text",
        "debug_info",
        "temperature",
        "include",
        "instructions",
        "max_output_tokens",
        "metadata",
        "parallel_tool_calls",
        "text",
        "top_p",
        "reasoning",
        "other_options",
    ]:
        if k in kwargs:
            res[k] = kwargs[k]

    return res


async def responses_stream_response(
    loop_runner_kwargs: _ResponsesLoopIterationRunnerKwargs,
    **kwargs,
) -> ResponsesLanguageModelStreamResponse:
    streaming_handler = loop_runner_kwargs["streaming_handler"]
    streaming_handler_kwargs = _extract_responses_streaming_kwargs(loop_runner_kwargs)
    streaming_handler_kwargs.update(**kwargs)

    return await streaming_handler.complete_with_references_async(
        **streaming_handler_kwargs
    )
