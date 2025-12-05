from typing import Any, Required

from openai.types.chat import ChatCompletionNamedToolChoiceParam
from typing_extensions import TypedDict

from unique_toolkit import LanguageModelToolDescription
from unique_toolkit.agentic.loop_runner.base import _LoopIterationRunnerKwargs
from unique_toolkit.chat.functions import LanguageModelStreamResponse
from unique_toolkit.chat.service import LanguageModelMessages
from unique_toolkit.content import ContentChunk


class _StreamingHandlerKwargs(TypedDict, total=False):
    messages: Required[LanguageModelMessages]
    model_name: Required[str]
    tools: list[LanguageModelToolDescription]
    content_chunks: list[ContentChunk]
    start_text: str
    debug_info: dict[str, Any]
    temperature: float
    tool_choice: ChatCompletionNamedToolChoiceParam
    other_options: dict[str, Any]


def _extract_streaming_kwargs(kwargs: _LoopIterationRunnerKwargs) -> _StreamingHandlerKwargs:
    res = _StreamingHandlerKwargs(
        messages=kwargs["messages"],
        model_name=kwargs["model"].name,
    )

    for k in [
        "tools",
        "content_chunks",
        "start_text",
        "debug_info",
        "temperature",
        "other_options",
    ]:
        if k in kwargs:
            res[k] = kwargs[k]

    return res


async def stream_response(
    loop_runner_kwargs: _LoopIterationRunnerKwargs,
    **kwargs,
) -> LanguageModelStreamResponse:
    streaming_handler = loop_runner_kwargs["streaming_handler"]
    streaming_hander_kwargs = _extract_streaming_kwargs(loop_runner_kwargs)
    streaming_hander_kwargs.update(**kwargs)

    return await streaming_handler.complete_with_references_async(
        **streaming_hander_kwargs
    )
