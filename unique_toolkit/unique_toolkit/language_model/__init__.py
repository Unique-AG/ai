from typing import TYPE_CHECKING, Any

from .constants import DOMAIN_NAME
from .default_language_model import DEFAULT_LANGUAGE_MODEL, DEFAULT_GPT_4o
from .functions import (
    stream_complete_with_references_openai as stream_complete_with_references_openai,
)
from .infos import LanguageModel, LanguageModelName, TypeDecoder, TypeEncoder
from .invocation_stats import (
    LanguageModelInvocationReport,
    LanguageModelInvocationStats,
)
from .prompt import (
    Prompt,
)
from .schemas import (
    LanguageModelAssistantMessage,
    LanguageModelCompletionChoice,
    LanguageModelFunction,
    LanguageModelFunctionCall,
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
    LanguageModelSystemMessage,
    LanguageModelTokenLimits,
    LanguageModelTokenUsage,
    LanguageModelTool,
    LanguageModelToolDescription,
    LanguageModelToolMessage,
    LanguageModelToolParameterProperty,
    LanguageModelToolParameters,
    LanguageModelUserMessage,
)
from .stream_transform import (
    NormalizationTransform,
    ReferenceInjectionTransform,
    StreamTransform,
    TextTransformPipeline,
)
from .utils import (
    convert_string_to_json,
    find_last_json_object,
)

if TYPE_CHECKING:
    from .service import LanguageModelService as LanguageModelService


def __getattr__(name: str) -> Any:
    if name == "LanguageModelService":
        from .service import LanguageModelService

        return LanguageModelService

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LanguageModel",
    "LanguageModelName",
    "Prompt",
    "LanguageModelAssistantMessage",
    "LanguageModelCompletionChoice",
    "LanguageModelFunction",
    "LanguageModelFunctionCall",
    "LanguageModelInvocationReport",
    "LanguageModelInvocationStats",
    "LanguageModelMessage",
    "LanguageModelMessageRole",
    "LanguageModelMessages",
    "LanguageModelResponse",
    "LanguageModelStreamResponse",
    "LanguageModelStreamResponseMessage",
    "LanguageModelSystemMessage",
    "LanguageModelTokenLimits",
    "LanguageModelTokenUsage",
    "LanguageModelTool",
    "LanguageModelToolDescription",
    "LanguageModelToolMessage",
    "LanguageModelToolParameterProperty",
    "LanguageModelToolParameters",
    "LanguageModelUserMessage",
    "LanguageModelService",
    "DOMAIN_NAME",
    "DEFAULT_LANGUAGE_MODEL",
    "DEFAULT_GPT_4o",
    "stream_complete_with_references_openai",
    "NormalizationTransform",
    "ReferenceInjectionTransform",
    "StreamTransform",
    "TextTransformPipeline",
    "convert_string_to_json",
    "find_last_json_object",
    "TypeDecoder",
    "TypeEncoder",
]
