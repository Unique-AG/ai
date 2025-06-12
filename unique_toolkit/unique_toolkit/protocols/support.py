from typing import Any, Protocol

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
        **kwargs,
    ) -> LanguageModelResponse: ...

    async def complete_async(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
        **kwargs,
    ) -> LanguageModelResponse: ...


class SupportUniqueStreamCompleteWithReferences(Protocol):
    def unique_stream_complete_with_references(
        self,
        company_id: str,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk],
        tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        **kwargs: dict[str, Any],
    ) -> LanguageModelStreamResponse: ...

    def unique_stream_complete_with_references_async(
        self,
        company_id: str,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk],
        tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        **kwargs: dict[str, Any],
    ) -> LanguageModelStreamResponse: ...
