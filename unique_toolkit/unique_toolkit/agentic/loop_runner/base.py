from typing import Any, Protocol, Required, Unpack, runtime_checkable

from openai.types.chat import ChatCompletionNamedToolChoiceParam
from openai.types.responses import (
    ResponseIncludable,
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
from unique_toolkit.language_model.invocation_stats import (
    LanguageModelInvocationStats,
)
from unique_toolkit.language_model.schemas import (
    ResponsesLanguageModelStreamResponse,
    ResponsesMessageInput,
)
from unique_toolkit.protocols.support import (
    ResponsesSupportCompleteWithReferences,
    SupportCompleteWithReferences,
)


@runtime_checkable
class SupportsInvocationStats(Protocol):
    """Optional capability for a loop iteration runner (or middleware wrapping
    one) that makes its own extra LLM call(s) beyond the main iteration
    response — e.g. a planning step. `unique_ai.py` checks for this via
    `isinstance` and, if present, folds the returned stats into the turn's
    accumulator; runners that don't make extra calls need not implement it."""

    def get_invocation_stats(self) -> list[LanguageModelInvocationStats]: ...


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
    messages: Required[ResponsesMessageInput]
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
