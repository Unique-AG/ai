from typing import Any, Awaitable, Protocol

from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import (
    LanguageModelMessages,
    LanguageModelName,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelTool,
    LanguageModelToolDescription,
)
from unique_toolkit.language_model.constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
    DEFAULT_COMPLETE_TIMEOUT,
)

# As soon as we have multiple, remember
# https://pypi.org/project/typing-protocol-intersection/
# to generate combinations of protocols without inheritance


class SupportsComplete(Protocol):
    def complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    ) -> LanguageModelResponse: ...

    async def complete_async(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    ) -> Awaitable[LanguageModelResponse]: ...


class SupportCompleteWithReferences(Protocol):
    def complete_with_references(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict[str, Any] = {},
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    ) -> LanguageModelStreamResponse: ...

    def complete_with_references_async(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict[str, Any] = {},
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    ) -> Awaitable[LanguageModelStreamResponse]: ...
