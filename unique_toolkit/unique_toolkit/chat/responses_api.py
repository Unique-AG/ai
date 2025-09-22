import logging
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
from pydantic import BaseModel

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
    LanguageModelMessageOptions,
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
            return _convert_message_to_openai(message.to_specific_message())
    return res


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
) -> _ResponsesParams:
    search_context = (
        _to_search_context(content_chunks) if content_chunks is not None else None
    )

    model = model_name.name if isinstance(model_name, LanguageModelName) else model_name

    tools_res = _convert_tools_to_openai(tools) if tools is not None else None

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
        temperature, model, search_context, messages_res, tools_res, reasoning
    )


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
    text: ResponseTextConfigParam | None,
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

    if params.temperature is not None:
        openai_options["temperature"] = params.temperature

    if params.reasoning is not None:
        openai_options["reasoning"] = params.reasoning

    if include is not None:
        openai_options["include"] = include

    if instructions is not None:
        openai_options["instructions"] = instructions

    if max_output_tokens is not None:
        openai_options["max_output_tokens"] = max_output_tokens

    if metadata is not None:
        openai_options["metadata"] = metadata

    if parallel_tool_calls is not None:
        openai_options["parallel_tool_calls"] = parallel_tool_calls

    if text is not None:
        openai_options["text"] = text

    if tool_choice is not None:
        openai_options["tool_choice"] = tool_choice

    if params.tools is not None:
        openai_options["tools"] = params.tools

    if top_p is not None:
        openai_options["top_p"] = top_p

    # allow any other openai.resources.responses.Response.create options
    if other_options is not None:
        openai_options.update(other_options)  # type: ignore

    options["options"] = openai_options

    return options


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
        text=text,
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
) -> ResponsesLanguageModelStreamResponse:
    responses_params = _prepare_responses_params_util(
        model_name=model_name,
        content_chunks=content_chunks,
        temperature=temperature,
        tools=tools,
        messages=messages,
        reasoning=reasoning,
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
        text=text,
        tool_choice=tool_choice,
        top_p=top_p,
        other_options=other_options,
    )

    return ResponsesLanguageModelStreamResponse.model_validate(
        await unique_sdk.Integrated.responses_stream_async(
            **responses_args,
        )
    )
