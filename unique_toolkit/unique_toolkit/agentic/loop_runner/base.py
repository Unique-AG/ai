from typing import Any, Protocol, Required, Sequence, Unpack

from openai.types.chat import ChatCompletionNamedToolChoiceParam
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
from unique_toolkit.chat.functions import LanguageModelStreamResponse
from unique_toolkit.chat.service import LanguageModelMessages
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageOptions,
    ResponsesLanguageModelStreamResponse,
)
from unique_toolkit.protocols.support import (
    ResponsesSupportCompleteWithReferences,
    SupportCompleteWithReferences,
)


class _LoopIterationRunnerKwargs(TypedDict, total=False):
    iteration_index: Required[int]
    streaming_handler: Required[SupportCompleteWithReferences]
    messages: Required[LanguageModelMessages]
    model: Required[LanguageModelInfo]
    tools: list[LanguageModelToolDescription]
    content_chunks: list[ContentChunk]
    start_text: str
    debug_info: dict[str, Any]
    temperature: float
    tool_choices: list[ChatCompletionNamedToolChoiceParam]
    other_options: dict[str, Any]


class LoopIterationRunner(Protocol):
    """
    A loop iteration runner is responsible for running a single iteration of the loop, and returning the stream response for that iteration.
    """

    async def __call__(
        self,
        **kwargs: Unpack[_LoopIterationRunnerKwargs],
    ) -> LanguageModelStreamResponse: ...


class _ResponsesLoopIterationRunnerKwargs(TypedDict, total=False):
    iteration_index: Required[int]
    streaming_handler: Required[ResponsesSupportCompleteWithReferences]
    messages: Required[
        str
        | LanguageModelMessages
        | Sequence[
            ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
        ]
    ]
    model: Required[LanguageModelInfo]
    tools: list[LanguageModelToolDescription | ToolParam]
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
    tool_choices: list[response_create_params.ToolChoice]
    top_p: float
    reasoning: Reasoning
    other_options: dict[str, Any]


class ResponsesLoopIterationRunner(Protocol):
    async def __call__(
        self,
        **kwargs: Unpack[_ResponsesLoopIterationRunnerKwargs],
    ) -> ResponsesLanguageModelStreamResponse: ...
