from typing import Protocol

from unique_toolkit.language_model import (
    LanguageModelMessages,
    LanguageModelName,
    LanguageModelResponse,
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
