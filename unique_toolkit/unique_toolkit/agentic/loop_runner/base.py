from typing import Any, Protocol, Required, Unpack

from openai.types.chat import ChatCompletionNamedToolChoiceParam
from typing_extensions import TypedDict

from unique_toolkit import LanguageModelToolDescription
from unique_toolkit.chat.functions import LanguageModelStreamResponse
from unique_toolkit.chat.service import LanguageModelMessages
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.protocols.support import (
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
