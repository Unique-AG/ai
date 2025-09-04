import copy
import logging
from datetime import UTC, datetime
from typing import Any, cast

import humps
import unique_sdk
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from pydantic import BaseModel

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.language_model import (
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
    LanguageModelTool,
    LanguageModelToolDescription,
)
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
    TemperatureBounds,
)
from unique_toolkit.language_model.reference import (
    add_references_to_message,
)

from .constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
    DEFAULT_COMPLETE_TIMEOUT,
)

logger = logging.getLogger(f"toolkit.language_model.{__name__}")


def complete(
    company_id: str,
    messages: LanguageModelMessages | list[ChatCompletionMessageParam],
    model_name: LanguageModelName | str,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    other_options: dict | None = None,
    structured_output_model: type[BaseModel] | None = None,
    structured_output_enforce_schema: bool = False,
) -> LanguageModelResponse:
    """Call the completion endpoint synchronously without streaming the response.

    Args:
    ----
        company_id (str): The company ID associated with the request.
        messages (LanguageModelMessages): The messages to complete.
        model_name (LanguageModelName | str): The model name to use for the completion.
        temperature (float): The temperature setting for the completion. Defaults to 0.
        timeout (int): The timeout value in milliseconds. Defaults to 240_000.
        tools (Optional[list[LanguageModelTool | LanguageModelToolDescription ]]): Optional list of tools to include.
        other_options (Optional[dict]): Additional options to use. Defaults to None.

    Returns:
    -------
        LanguageModelResponse: The response object containing the completed result.

    """
    options, model, messages_dict, _ = _prepare_all_completions_params_util(
        messages=messages,
        model_name=model_name,
        temperature=temperature,
        tools=tools,
        other_options=other_options,
        structured_output_model=structured_output_model,
        structured_output_enforce_schema=structured_output_enforce_schema,
    )

    try:
        response = unique_sdk.ChatCompletion.create(
            company_id=company_id,
            model=model,
            messages=cast(
                "list[unique_sdk.Integrated.ChatCompletionRequestMessage]",
                messages_dict,
            ),
            timeout=timeout,
            options=options,  # type: ignore
        )
        return LanguageModelResponse(**response)
    except Exception as e:
        logger.error(f"Error completing: {e}")
        raise e


async def complete_async(
    company_id: str,
    messages: LanguageModelMessages | list[ChatCompletionMessageParam],
    model_name: LanguageModelName | str,
    user_id: str | None = None,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    other_options: dict | None = None,
    structured_output_model: type[BaseModel] | None = None,
    structured_output_enforce_schema: bool = False,
) -> LanguageModelResponse:
    """Call the completion endpoint asynchronously without streaming the response.

    This method sends a request to the completion endpoint using the provided messages, model name,
    temperature, timeout, and optional tools. It returns a `LanguageModelResponse` object containing
    the completed result.

    Args:
    ----
        company_id (str): The company ID associated with the request.
        messages (LanguageModelMessages): The messages to complete.
        model_name (LanguageModelName | str): The model name to use for the completion.
        temperature (float): The temperature setting for the completion. Defaults to 0.
        timeout (int): The timeout value in milliseconds for the request. Defaults to 240_000.
        tools (Optional[list[LanguageModelTool | LanguageModelToolDescription ]]): Optional list of tools to include in the request.
        other_options (Optional[dict]): The other options to use. Defaults to None.

    Returns:
    -------
        LanguageModelResponse: The response object containing the completed result.

    Raises:
    ------
        Exception: If an error occurs during the request, an exception is raised
        and logged.

    """
    options, model, messages_dict, _ = _prepare_all_completions_params_util(
        messages=messages,
        model_name=model_name,
        temperature=temperature,
        tools=tools,
        other_options=other_options,
        structured_output_model=structured_output_model,
        structured_output_enforce_schema=structured_output_enforce_schema,
    )

    try:
        response = await unique_sdk.ChatCompletion.create_async(
            company_id=company_id,
            user_id=user_id,
            model=model,
            messages=cast(
                "list[unique_sdk.Integrated.ChatCompletionRequestMessage]",
                messages_dict,
            ),
            timeout=timeout,
            options=options,  # type: ignore
        )
        return LanguageModelResponse(**response)
    except Exception as e:
        logger.exception(f"Error completing: {e}")
        raise e


def _add_tools_to_options(
    options: dict,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None,
) -> dict:
    if tools:
        options["tools"] = [
            {
                "type": "function",
                "function": tool.model_dump(exclude_none=True),
            }
            for tool in tools
        ]
    return options


SearchContext = list[unique_sdk.Integrated.SearchResult]


def _to_search_context(
    chunks: list[ContentChunk],
) -> SearchContext | None:
    if not chunks:
        return None
    return [
        unique_sdk.Integrated.SearchResult(
            id=chunk.id,
            chunkId=chunk.chunk_id,
            key=chunk.key,
            title=chunk.title,
            url=chunk.url,
            startPage=chunk.start_page,
            endPage=chunk.end_page,
            order=chunk.order,
            object=chunk.object,
        )
        for chunk in chunks
    ]


def _add_response_format_to_options(
    options: dict,
    structured_output_model: type[BaseModel],
    structured_output_enforce_schema: bool = False,
) -> dict:
    options["responseFormat"] = {
        "type": "json_schema",
        "json_schema": {
            "name": structured_output_model.__name__,
            "strict": structured_output_enforce_schema,
            "schema": structured_output_model.model_json_schema(),
        },
    }
    return options


def _prepare_completion_params_util(
    messages: LanguageModelMessages,
    model_name: LanguageModelName | str,
    temperature: float,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    other_options: dict | None = None,
    content_chunks: list[ContentChunk] | None = None,
    structured_output_model: type[BaseModel] | None = None,
    structured_output_enforce_schema: bool = False,
) -> tuple[dict, str, dict, SearchContext | None]:
    """Prepare common parameters for completion requests.

    Returns
    -------
        tuple containing:
        - options (dict): Combined options including tools and temperature
        - model (str): Resolved model name
        - messages_dict (dict): Processed messages
        - search_context (dict | None): Processed content chunks if provided

    """
    options = _add_tools_to_options({}, tools)

    if structured_output_model:
        options = _add_response_format_to_options(
            options,
            structured_output_model,
            structured_output_enforce_schema,
        )
    options["temperature"] = temperature
    if other_options:
        options.update(other_options)

    model = (
        model_name.value if isinstance(model_name, LanguageModelName) else model_name
    )

    messages_dict = messages.model_dump(
        exclude_none=True,
        by_alias=True,
    )

    search_context = (
        _to_search_context(content_chunks) if content_chunks is not None else None
    )

    return options, model, messages_dict, search_context


def _prepare_openai_completion_params_util(
    model_name: LanguageModelName | str,
    temperature: float,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    other_options: dict | None = None,
    content_chunks: list[ContentChunk] | None = None,
    structured_output_model: type[BaseModel] | None = None,
    structured_output_enforce_schema: bool = False,
) -> tuple[dict, str, SearchContext | None]:
    """Prepare common parameters for completion requests.

    Returns
    -------
        tuple containing:
        - options (dict): Combined options including tools and temperature
        - model (str): Resolved model name
        - messages_dict (dict): Processed messages
        - search_context (dict | None): Processed content chunks if provided

    """
    options = _add_tools_to_options({}, tools)

    if structured_output_model:
        options = _add_response_format_to_options(
            options,
            structured_output_model,
            structured_output_enforce_schema,
        )
    options["temperature"] = temperature
    if other_options:
        options.update(other_options)

    model = (
        model_name.value if isinstance(model_name, LanguageModelName) else model_name
    )

    search_context = (
        _to_search_context(content_chunks) if content_chunks is not None else None
    )

    return options, model, search_context


def __camelize_keys(data):
    """Recursively camelize dictionary keys using humps."""
    if isinstance(data, dict):
        return {humps.camelize(k): __camelize_keys(v) for k, v in data.items()}
    if isinstance(data, list):
        return [__camelize_keys(item) for item in data]
    return data


def _clamp_temperature(
    temperature: float, temperature_bounds: TemperatureBounds
) -> float:
    temperature = max(temperature_bounds.min_temperature, temperature)
    temperature = min(temperature_bounds.max_temperature, temperature)
    return round(temperature, 2)


def _prepare_other_options(
    other_options: dict | None,
    default_options: dict,
) -> dict:
    options = default_options
    if other_options is not None:
        options.update(other_options)
    return options


def _prepare_all_completions_params_util(
    messages: LanguageModelMessages | list[ChatCompletionMessageParam],
    model_name: LanguageModelName | str,
    temperature: float,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    other_options: dict | None = None,
    content_chunks: list[ContentChunk] | None = None,
    structured_output_model: type[BaseModel] | None = None,
    structured_output_enforce_schema: bool = False,
) -> tuple[
    dict,
    str,
    list[unique_sdk.Integrated.ChatCompletionRequestMessage],
    SearchContext | None,
]:
    model_info = None
    if isinstance(model_name, LanguageModelName):
        model_info = LanguageModelInfo.from_name(model_name)
        other_options = _prepare_other_options(
            other_options, model_info.default_options
        )

    if isinstance(messages, LanguageModelMessages):
        options, model, messages_dict, search_context = _prepare_completion_params_util(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            tools=tools,
            content_chunks=content_chunks,
            other_options=other_options,
            structured_output_model=structured_output_model,
            structured_output_enforce_schema=structured_output_enforce_schema,
        )
    else:
        options, model, search_context = _prepare_openai_completion_params_util(
            model_name=model_name,
            temperature=temperature,
            tools=tools,
            content_chunks=content_chunks,
            other_options=other_options,
            structured_output_model=structured_output_model,
            structured_output_enforce_schema=structured_output_enforce_schema,
        )
        messages_dict = __camelize_keys(messages.copy())

    if (
        model_info is not None
        and model_info.temperature_bounds is not None
        and "temperature" in options
    ):
        options["temperature"] = _clamp_temperature(
            temperature, model_info.temperature_bounds
        )

    integrated_messages = cast(
        "list[unique_sdk.Integrated.ChatCompletionRequestMessage]",
        messages_dict,
    )

    return options, model, integrated_messages, search_context


def complete_with_references(
    company_id: str,
    messages: LanguageModelMessages,
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] | None = None,
    debug_dict: dict = {},
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    start_text: str | None = None,
    other_options: dict[str, Any] | None = None,
) -> LanguageModelStreamResponse:
    # Use toolkit language model functions for chat completion
    response = complete(
        company_id=company_id,
        model_name=model_name,
        messages=messages,
        temperature=temperature,
        timeout=timeout,
        tools=tools,
        other_options=other_options,
    )

    return _create_language_model_stream_response_with_references(
        response=response,
        content_chunks=content_chunks,
        start_text=start_text,
    )


async def complete_with_references_async(
    company_id: str,
    user_id: str,
    messages: LanguageModelMessages,
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] | None = None,
    debug_dict: dict | None = None,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
    start_text: str | None = None,
    other_options: dict[str, Any] | None = None,
) -> LanguageModelStreamResponse:
    # Use toolkit language model functions for chat completion
    response = await complete_async(
        company_id=company_id,
        user_id=user_id,
        model_name=model_name,
        messages=messages,
        temperature=temperature,
        timeout=timeout,
        tools=tools,
        other_options=other_options,
    )

    return _create_language_model_stream_response_with_references(
        response=response,
        content_chunks=content_chunks,
        start_text=start_text,
    )


def _create_language_model_stream_response_with_references(
    response: LanguageModelResponse,
    content_chunks: list[ContentChunk] | None = None,
    start_text: str | None = None,
):
    content = response.choices[0].message.content
    content_chunks = content_chunks or []

    if content is None:
        raise ValueError("Content is None, which is not supported")
    if isinstance(content, list):
        raise ValueError("Content is a list, which is not supported")
    content = start_text or "" + str(content)

    message = ChatMessage(
        id="msg_unknown",
        text=copy.deepcopy(content),
        role=ChatMessageRole.ASSISTANT,
        created_at=datetime.now(UTC),
        chat_id="chat_unknown",
    )

    message, __ = add_references_to_message(
        message=message,
        search_context=content_chunks,
    )

    stream_response_message = LanguageModelStreamResponseMessage(
        id="stream_unknown",
        previous_message_id=None,
        role=LanguageModelMessageRole.ASSISTANT,
        text=message.content or "",
        original_text=content,
        references=[
            ContentReference(**u.model_dump()) for u in message.references or []
        ],
    )

    tool_calls = [r.function for r in response.choices[0].message.tool_calls or []]
    tool_calls = tool_calls if len(tool_calls) > 0 else None

    return LanguageModelStreamResponse(
        message=stream_response_message,
        tool_calls=tool_calls,
    )


def _prepare_responses_params_util(
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] | None,
    temperature: float | None,
) -> tuple[float | None, str, list[unique_sdk.Integrated.SearchResult] | None]:
    search_context = (
        _to_search_context(content_chunks) if content_chunks is not None else None
    )

    model = model_name.name if isinstance(model_name, LanguageModelName) else model_name

    if isinstance(model_name, LanguageModelName):
        model_info = LanguageModelInfo.from_name(model_name)

        if model_info.temperature_bounds is not None and temperature is not None:
            temperature = _clamp_temperature(temperature, model_info.temperature_bounds)

    return temperature, model, search_context
