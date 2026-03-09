import json
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, NamedTuple, Sequence

import unique_sdk
from openai.types.responses import (
    ResponseIncludable,
    ResponseInputItemParam,
    ResponseInputParam,
    ResponseOutputItem,
    ResponseTextConfigParam,
    ToolParam,
    response_create_params,
)
from openai.types.shared_params import Metadata, Reasoning
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
)

from unique_toolkit._common.execution import (
    failsafe,
)
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
)
from unique_toolkit.language_model.functions import (
    SearchContext,
    _clamp_temperature,
    _to_search_context,
)
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelMessageOptions,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelToolDescription,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
    ResponsesLanguageModelStreamResponse,
)

logger = logging.getLogger(__name__)


def _convert_tools_to_openai(
    tools: Sequence[LanguageModelToolDescription | ToolParam],
) -> list[ToolParam]:
    openai_tools = []
    for tool in tools:
        if isinstance(tool, LanguageModelToolDescription):
            openai_tools.append(tool.to_openai(mode="responses"))
        else:
            openai_tools.append(tool)
    return openai_tools


def _convert_message_to_openai(
    message: LanguageModelMessageOptions,
) -> ResponseInputParam:
    res = []
    match message:
        case LanguageModelAssistantMessage():
            return message.to_openai(mode="responses")  # type: ignore
        case (
            LanguageModelUserMessage()
            | LanguageModelSystemMessage()
            | LanguageModelToolMessage()
        ):
            return [message.to_openai(mode="responses")]
        case _:
            return _convert_message_to_openai(_convert_to_specific_message(message))
    return res


def _convert_to_specific_message(
    message: LanguageModelMessage,
) -> "LanguageModelSystemMessage | LanguageModelUserMessage | LanguageModelAssistantMessage":
    match message.role:
        case LanguageModelMessageRole.SYSTEM:
            return LanguageModelSystemMessage(content=message.content)
        case LanguageModelMessageRole.USER:
            return LanguageModelUserMessage(content=message.content)
        case LanguageModelMessageRole.ASSISTANT:
            return LanguageModelAssistantMessage(content=message.content)
        case LanguageModelMessageRole.TOOL:
            raise ValueError(
                "Cannot convert message with role `tool`. Please use `LanguageModelToolMessage` instead."
            )


def _convert_messages_to_openai(
    messages: Sequence[
        ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
    ],
) -> ResponseInputParam:
    res = []
    for message in messages:
        if isinstance(message, LanguageModelMessageOptions):
            res.extend(_convert_message_to_openai(message))
        elif isinstance(
            message, dict
        ):  # Openai uses dicts for their input and BaseModel as output
            res.append(message)
        else:
            assert isinstance(message, BaseModel)
            res.append(message.model_dump(exclude_defaults=True))

    return res


class _ResponsesParams(NamedTuple):
    temperature: float
    model_name: str
    search_context: SearchContext | None
    messages: str | ResponseInputParam
    tools: list[ToolParam] | None
    reasoning: Reasoning | None
    text: ResponseTextConfigParam | None


def _prepare_responses_params_util(
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] | None,
    temperature: float,
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None,
    messages: str
    | LanguageModelMessages
    | Sequence[
        ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
    ],
    reasoning: Reasoning | None,
    text: ResponseTextConfigParam | None,
    other_options: dict | None = None,
) -> _ResponsesParams:
    search_context = (
        _to_search_context(content_chunks) if content_chunks is not None else None
    )

    model = model_name.name if isinstance(model_name, LanguageModelName) else model_name

    tools_res = _convert_tools_to_openai(tools) if tools is not None else None

    if other_options is not None:
        # Key word argument takes precedence
        reasoning = reasoning or _attempt_extract_reasoning_from_options(other_options)
        text = text or _attempt_extract_verbosity_from_options(other_options)

    if isinstance(model_name, LanguageModelName):
        model_info = LanguageModelInfo.from_name(model_name)

        if model_info.temperature_bounds is not None and temperature is not None:
            temperature = _clamp_temperature(temperature, model_info.temperature_bounds)

        if (
            reasoning is None
            and model_info.default_options is not None
            and "reasoning_effort" in model_info.default_options
        ):
            reasoning = Reasoning(effort=model_info.default_options["reasoning_effort"])

        if (
            reasoning is not None
            and tools_res is not None
            and any(tool["type"] == "code_interpreter" for tool in tools_res)
            and "effort" in reasoning
            and reasoning["effort"] == "minimal"
        ):
            logger.warning(
                "Code interpreter cannot be used with `minimal` effort. Switching to `low`."
            )
            reasoning["effort"] = (
                "low"  # Code interpreter cannot be used with minimal effort
            )

    messages_res = None
    if isinstance(messages, LanguageModelMessages):
        messages_res = _convert_messages_to_openai(messages.root)
    elif isinstance(messages, list):
        messages_res = _convert_messages_to_openai(messages)
    else:
        assert isinstance(messages, str)
        messages_res = messages

    return _ResponsesParams(
        temperature, model, search_context, messages_res, tools_res, reasoning, text
    )


@failsafe(
    failure_return_value=None,
    exceptions=(ValidationError,),
    log_exc_info=False,
    logger=logger,
)
def _attempt_extract_reasoning_from_options(
    options: dict[str, Any],
) -> Reasoning | None:
    reasoning: dict[str, Any] | str | None = None

    # Responses API
    if "reasoning" in options:
        reasoning = options["reasoning"]
        # Handle case where reasoning is stored as JSON string (UI limitation)
        if isinstance(reasoning, str):
            try:
                reasoning = json.loads(reasoning)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    f"Failed to parse reasoning as JSON string: {reasoning}. "
                    "Continuing with raw value."
                )

    # Completions API
    elif "reasoning_effort" in options:
        reasoning = {"effort": options["reasoning_effort"]}
    if "reasoningEffort" in options:
        reasoning = {"effort": options["reasoningEffort"]}

    if reasoning is not None:
        return TypeAdapter(Reasoning).validate_python(reasoning)

    return None


@failsafe(
    failure_return_value=None,
    exceptions=(ValidationError,),
    log_exc_info=False,
    logger=logger,
)
def _attempt_extract_verbosity_from_options(
    options: dict[str, Any],
) -> ResponseTextConfigParam | None:
    if "verbosity" in options:
        return TypeAdapter(ResponseTextConfigParam).validate_python(
            {"verbosity": options["verbosity"]}
        )

    # Responses API
    if "text" in options:
        text_config: dict[str, Any] | str = options["text"]
        # Handle case where text is stored as JSON string (UI limitation)
        if isinstance(text_config, str):
            try:
                text_config = json.loads(text_config)
                return TypeAdapter(ResponseTextConfigParam).validate_python(text_config)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    f"Failed to parse text as JSON string: {text_config}. "
                    "Continuing with raw value."
                )
        if isinstance(text_config, dict):
            return TypeAdapter(ResponseTextConfigParam).validate_python(text_config)

    return None


def _prepare_responses_args(
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    params: _ResponsesParams,
    debug_info: dict | None,
    start_text: str | None,
    include: list[ResponseIncludable] | None,
    instructions: str | None,
    max_output_tokens: int | None,
    metadata: Metadata | None,
    parallel_tool_calls: bool | None,
    tool_choice: response_create_params.ToolChoice | None,
    top_p: float | None,
    other_options: dict | None = None,
) -> dict[str, Any]:
    options = {}

    options["company_id"] = company_id
    options["user_id"] = user_id

    options["model"] = params.model_name

    if params.search_context is not None:
        options["searchContext"] = params.search_context

    options["chatId"] = chat_id
    options["assistantId"] = assistant_id
    options["assistantMessageId"] = assistant_message_id
    options["userMessageId"] = user_message_id

    if debug_info is not None:
        options["debugInfo"] = debug_info
    if start_text is not None:
        options["startText"] = start_text

    options["input"] = params.messages

    openai_options: unique_sdk.Integrated.CreateStreamResponsesOpenaiParams = {}

    explicit_options = {
        "temperature": params.temperature,
        "reasoning": params.reasoning,
        "text": params.text,
        "include": include,
        "instructions": instructions,
        "max_output_tokens": max_output_tokens,
        "metadata": metadata,
        "parallel_tool_calls": parallel_tool_calls,
        "tool_choice": tool_choice,
        "tools": params.tools,
        "top_p": top_p,
    }

    openai_options.update({k: v for k, v in explicit_options.items() if v is not None})  # type: ignore[arg-type]

    # allow any other openai.resources.responses.Response.create options
    if other_options is not None:
        for k, v in other_options.items():
            openai_options.setdefault(k, v)  # type: ignore

    options["options"] = openai_options

    return options


_RATE_LIMIT_KEYWORDS = ("too_many_requests", "too many requests", "ratelimitreached")


class RateLimitRetryConfig(BaseSettings):
    """Config for Responses API rate-limit retry. Set via env vars with prefix RATE_LIMIT_RETRY_."""

    initial_delay_seconds: float = Field(
        default=30.0,
        description="First wait after SDK retries exhausted. Backoff then 2x (30→60→120s).",
    )
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Total attempts (1 initial + retries). Default 3 = 2 retries. Set to 1 to disable.",
    )
    log_message_on_retry: bool = Field(
        default=True,
        description="Write a message-log entry when a retry is about to sleep (e.g. 'Retrying in 30s').",
    )

    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_RETRY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


rate_limit_retry_config = RateLimitRetryConfig()


def _rate_limit_wait(retry_state: RetryCallState) -> float:
    """Exponential backoff with up to 10% jitter: initial_delay → 2x → 4x."""
    n = retry_state.attempt_number - 1  # 0-indexed
    base = rate_limit_retry_config.initial_delay_seconds * (2.0**n)
    return base + random.uniform(0.0, base * 0.1)


async def _responses_stream_with_rate_limit_retry(
    responses_args: dict[str, Any],
    model_name: str,
    on_rate_limit_retry: Callable[[int, float], Awaitable[None]] | None = None,
) -> Any:
    """Wrap responses_stream_async with exponential backoff for rate-limit errors.

    The SDK already retries 3× (1s/2s/4s) before raising. This layer adds further
    retries with longer delays, which are needed for models with tighter RPM limits
    (e.g. GPT-4o) when large-token requests (web search, code execution) are in the loop.

    Args:
        responses_args: Keyword arguments forwarded to responses_stream_async.
        model_name: Model name used in log messages.
        on_rate_limit_retry: Optional async callback invoked before each retry sleep.
            Receives (attempt_1based, wait_seconds). Useful for writing a message-log
            entry so the user sees progress during long waits.
    """

    def _is_rate_limit(exc: BaseException) -> bool:
        return isinstance(exc, unique_sdk.APIError) and any(
            kw in str(exc).lower() for kw in _RATE_LIMIT_KEYWORDS
        )

    max_attempts = rate_limit_retry_config.max_attempts
    max_retries = max_attempts - 1

    def _log_attempt(retry_state: RetryCallState) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if exc is None:
            return
        logger.error(
            "responses_stream_async error on toolkit attempt %d/%d "
            "model=%s code=%s http_status=%s is_rate_limit=%s original_error=%r",
            retry_state.attempt_number,
            max_attempts,
            model_name,
            getattr(exc, "code", None),
            getattr(exc, "http_status", None),
            _is_rate_limit(exc),
            getattr(exc, "original_error", None),
        )

    async def _before_sleep(retry_state: RetryCallState) -> None:
        wait_secs = retry_state.upcoming_sleep
        logger.warning(
            "Rate limit hit for model=%s. Toolkit-level retry %d/%d in %.1fs",
            model_name,
            retry_state.attempt_number,
            max_retries,
            wait_secs,
        )
        if on_rate_limit_retry is not None:
            await on_rate_limit_retry(retry_state.attempt_number, wait_secs)

    async def _call() -> Any:
        return await unique_sdk.Integrated.responses_stream_async(**responses_args)

    return await AsyncRetrying(
        retry=retry_if_exception(_is_rate_limit),
        stop=stop_after_attempt(max_attempts),
        wait=_rate_limit_wait,
        after=_log_attempt,
        before_sleep=_before_sleep,
        reraise=True,
    )(_call)


def stream_responses_with_references(
    *,
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    model_name: LanguageModelName | str,
    messages: str
    | LanguageModelMessages
    | Sequence[
        ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
    ],
    content_chunks: list[ContentChunk] | None = None,
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None = None,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    debug_info: dict | None = None,
    start_text: str | None = None,
    include: list[ResponseIncludable] | None = None,
    instructions: str | None = None,
    max_output_tokens: int | None = None,
    metadata: Metadata | None = None,
    parallel_tool_calls: bool | None = None,
    text: ResponseTextConfigParam | None = None,
    tool_choice: response_create_params.ToolChoice | None = None,
    top_p: float | None = None,
    reasoning: Reasoning | None = None,
    other_options: dict | None = None,
) -> ResponsesLanguageModelStreamResponse:
    responses_params = _prepare_responses_params_util(
        model_name=model_name,
        content_chunks=content_chunks,
        temperature=temperature,
        tools=tools,
        messages=messages,
        reasoning=reasoning,
        text=text,
        other_options=other_options,
    )

    responses_args = _prepare_responses_args(
        company_id=company_id,
        user_id=user_id,
        assistant_message_id=assistant_message_id,
        user_message_id=user_message_id,
        chat_id=chat_id,
        assistant_id=assistant_id,
        params=responses_params,
        debug_info=debug_info,
        start_text=start_text,
        include=include,
        instructions=instructions,
        max_output_tokens=max_output_tokens,
        metadata=metadata,
        parallel_tool_calls=parallel_tool_calls,
        tool_choice=tool_choice,
        top_p=top_p,
        other_options=other_options,
    )

    return ResponsesLanguageModelStreamResponse.model_validate(
        unique_sdk.Integrated.responses_stream(
            **responses_args,
        )
    )


async def stream_responses_with_references_async(
    *,
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    model_name: LanguageModelName | str,
    messages: str
    | LanguageModelMessages
    | Sequence[
        ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
    ],
    content_chunks: list[ContentChunk] | None = None,
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None = None,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    debug_info: dict | None = None,
    start_text: str | None = None,
    include: list[ResponseIncludable] | None = None,
    instructions: str | None = None,
    max_output_tokens: int | None = None,
    metadata: Metadata | None = None,
    parallel_tool_calls: bool | None = None,
    text: ResponseTextConfigParam | None = None,
    tool_choice: response_create_params.ToolChoice | None = None,
    top_p: float | None = None,
    reasoning: Reasoning | None = None,
    other_options: dict | None = None,
    on_rate_limit_retry: Callable[[int, float], Awaitable[None]] | None = None,
) -> ResponsesLanguageModelStreamResponse:
    responses_params = _prepare_responses_params_util(
        model_name=model_name,
        content_chunks=content_chunks,
        temperature=temperature,
        tools=tools,
        messages=messages,
        reasoning=reasoning,
        text=text,
        other_options=other_options,
    )

    responses_args = _prepare_responses_args(
        company_id=company_id,
        user_id=user_id,
        assistant_message_id=assistant_message_id,
        user_message_id=user_message_id,
        chat_id=chat_id,
        assistant_id=assistant_id,
        params=responses_params,
        debug_info=debug_info,
        start_text=start_text,
        include=include,
        instructions=instructions,
        max_output_tokens=max_output_tokens,
        metadata=metadata,
        parallel_tool_calls=parallel_tool_calls,
        tool_choice=tool_choice,
        top_p=top_p,
        other_options=other_options,
    )

    logger.info(
        "Calling responses_stream_async model=%s",
        responses_params.model_name,
    )
    return ResponsesLanguageModelStreamResponse.model_validate(
        await _responses_stream_with_rate_limit_retry(
            responses_args=responses_args,
            model_name=responses_params.model_name,
            on_rate_limit_retry=on_rate_limit_retry,
        )
    )
