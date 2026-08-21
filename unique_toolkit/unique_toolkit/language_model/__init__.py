# pyright: reportImportCycles=false
from typing import TYPE_CHECKING, cast

from .constants import DOMAIN_NAME
from .default_language_model import DEFAULT_LANGUAGE_MODEL, DEFAULT_GPT_4o
from .functions import (
    stream_complete_with_references_openai as stream_complete_with_references_openai,
)
from .infos import LanguageModel, LanguageModelName, TypeDecoder, TypeEncoder
from .invocation_stats import (
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
    from collections.abc import Callable as _Callable

    from .dynamic import (
        ActiveLanguageModelConfigurationError as ActiveLanguageModelConfigurationError,
    )
    from .dynamic import (
        ensure_company_id as ensure_company_id,
    )
    from .dynamic import (
        ensure_sdk_initialized as ensure_sdk_initialized,
    )
    from .dynamic import (
        get_active_language_models_async as get_active_language_models_async,
    )
    from .dynamic import (
        get_default_active_language_model_async as get_default_active_language_model_async,
    )
    from .service import LanguageModelService as LanguageModelService

    get_schema_with_available_language_models: _Callable[..., dict[str, object]]

_DYNAMIC_EXPORTS = {
    "ActiveLanguageModelConfigurationError",
    "ensure_company_id",
    "ensure_sdk_initialized",
    "get_active_language_models_async",
    "get_default_active_language_model_async",
    "get_schema_with_available_language_models",
}


def __getattr__(name: str) -> object:
    if name == "LanguageModelService":
        from .service import LanguageModelService

        return LanguageModelService

    if name in _DYNAMIC_EXPORTS:
        from . import dynamic

        return cast(object, getattr(dynamic, name))

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LanguageModel",
    "LanguageModelName",
    "ActiveLanguageModelConfigurationError",
    "ensure_company_id",
    "ensure_sdk_initialized",
    "get_active_language_models_async",
    "get_default_active_language_model_async",
    "get_schema_with_available_language_models",
    "Prompt",
    "LanguageModelAssistantMessage",
    "LanguageModelCompletionChoice",
    "LanguageModelFunction",
    "LanguageModelFunctionCall",
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
