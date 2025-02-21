import logging
from typing import Optional, Type, cast

import unique_sdk
from pydantic import BaseModel

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.evaluators import DOMAIN_NAME
from unique_toolkit.language_model.constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
    DEFAULT_COMPLETE_TIMEOUT,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelTool,
)

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


def complete(
    company_id: str,
    messages: LanguageModelMessages,
    model_name: LanguageModelName | str,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: Optional[list[LanguageModelTool]] = None,
    other_options: Optional[dict] = None,
    structured_output_model: Optional[Type[BaseModel]] = None,
    structured_output_enforce_schema: bool = False,
) -> LanguageModelResponse:
    """
    Calls the completion endpoint synchronously without streaming the response.

    Args:
        company_id (str): The company ID associated with the request.
        messages (LanguageModelMessages): The messages to complete.
        model_name (LanguageModelName | str): The model name to use for the completion.
        temperature (float): The temperature setting for the completion. Defaults to 0.
        timeout (int): The timeout value in milliseconds. Defaults to 240_000.
        tools (Optional[list[LanguageModelTool]]): Optional list of tools to include.
        other_options (Optional[dict]): Additional options to use. Defaults to None.

    Returns:
        LanguageModelResponse: The response object containing the completed result.
    """
    options, model, messages_dict, _ = _prepare_completion_params_util(
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
                list[unique_sdk.Integrated.ChatCompletionRequestMessage],
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
    messages: LanguageModelMessages,
    model_name: LanguageModelName | str,
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: Optional[list[LanguageModelTool]] = None,
    other_options: Optional[dict] = None,
    structured_output_model: Optional[Type[BaseModel]] = None,
    structured_output_enforce_schema: bool = False,
) -> LanguageModelResponse:
    """
    Calls the completion endpoint asynchronously without streaming the response.

    This method sends a request to the completion endpoint using the provided messages, model name,
    temperature, timeout, and optional tools. It returns a `LanguageModelResponse` object containing
    the completed result.

    Args:
        company_id (str): The company ID associated with the request.
        messages (LanguageModelMessages): The messages to complete.
        model_name (LanguageModelName | str): The model name to use for the completion.
        temperature (float): The temperature setting for the completion. Defaults to 0.
        timeout (int): The timeout value in milliseconds for the request. Defaults to 240_000.
        tools (Optional[list[LanguageModelTool]]): Optional list of tools to include in the request.
        other_options (Optional[dict]): The other options to use. Defaults to None.

    Returns:
        LanguageModelResponse: The response object containing the completed result.

    Raises:
        Exception: If an error occurs during the request, an exception is raised and logged.
    """
    options, model, messages_dict, _ = _prepare_completion_params_util(
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
            model=model,
            messages=cast(
                list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                messages_dict,
            ),
            timeout=timeout,
            options=options,  # type: ignore
        )
        return LanguageModelResponse(**response)
    except Exception as e:
        logger.error(f"Error completing: {e}")  # type: ignore
        raise e


def stream_complete_to_chat(
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    messages: LanguageModelMessages,
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] = [],
    debug_info: dict = {},
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: Optional[list[LanguageModelTool]] = None,
    start_text: Optional[str] = None,
    other_options: Optional[dict] = None,
) -> LanguageModelStreamResponse:
    """
    Streams a completion synchronously.

    Args:
        company_id (str): The company ID associated with the request.
        user_id (str): The user ID for the request.
        assistant_message_id (str): The assistant message ID.
        user_message_id (str): The user message ID.
        chat_id (str): The chat ID.
        assistant_id (str): The assistant ID.
        messages (LanguageModelMessages): The messages to complete.
        model_name (LanguageModelName | str): The model name.
        content_chunks (list[ContentChunk]): Content chunks for context.
        debug_info (dict): Debug information.
        temperature (float): Temperature setting.
        timeout (int): Timeout in milliseconds.
        tools (Optional[list[LanguageModelTool]]): Optional tools.
        start_text (Optional[str]): Starting text.
        other_options (Optional[dict]): Additional options.

    Returns:
        LanguageModelStreamResponse: The streaming response object.
    """
    options, model, messages_dict, search_context = _prepare_completion_params_util(
        messages=messages,
        model_name=model_name,
        temperature=temperature,
        tools=tools,
        other_options=other_options,
        content_chunks=content_chunks,
    )

    try:
        response = unique_sdk.Integrated.chat_stream_completion(
            user_id=user_id,
            company_id=company_id,
            assistantMessageId=assistant_message_id,
            userMessageId=user_message_id,
            messages=cast(
                list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                messages_dict,
            ),
            chatId=chat_id,
            searchContext=search_context,
            model=model,
            timeout=timeout,
            assistantId=assistant_id,
            debugInfo=debug_info,
            options=options,  # type: ignore
            startText=start_text,
        )
        return LanguageModelStreamResponse(**response)
    except Exception as e:
        logger.error(f"Error streaming completion: {e}")
        raise e


async def stream_complete_to_chat_async(
    company_id: str,
    user_id: str,
    assistant_message_id: str,
    user_message_id: str,
    chat_id: str,
    assistant_id: str,
    messages: LanguageModelMessages,
    model_name: LanguageModelName | str,
    content_chunks: list[ContentChunk] = [],
    debug_info: dict = {},
    temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
    timeout: int = DEFAULT_COMPLETE_TIMEOUT,
    tools: Optional[list[LanguageModelTool]] = None,
    start_text: Optional[str] = None,
    other_options: Optional[dict] = None,
) -> LanguageModelStreamResponse:
    """
    Streams a completion asynchronously.

    Args: [same as stream_complete]

    Returns:
        LanguageModelStreamResponse: The streaming response object.
    """
    options, model, messages_dict, search_context = _prepare_completion_params_util(
        messages=messages,
        model_name=model_name,
        temperature=temperature,
        tools=tools,
        other_options=other_options,
        content_chunks=content_chunks,
    )

    try:
        response = await unique_sdk.Integrated.chat_stream_completion_async(
            user_id=user_id,
            company_id=company_id,
            assistantMessageId=assistant_message_id,
            userMessageId=user_message_id,
            messages=cast(
                list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                messages_dict,
            ),
            chatId=chat_id,
            searchContext=search_context,
            model=model,
            timeout=timeout,
            assistantId=assistant_id,
            debugInfo=debug_info,
            options=options,  # type: ignore
            startText=start_text,
        )
        return LanguageModelStreamResponse(**response)
    except Exception as e:
        logger.error(f"Error streaming completion: {e}")
        raise e


def _add_tools_to_options(
    options: dict,
    tools: Optional[list[LanguageModelTool]],
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


def _to_search_context(chunks: list[ContentChunk]) -> dict | None:
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
        )  # type: ignore
        for chunk in chunks
    ]


def _add_response_format_to_options(
    options: dict,
    structured_output_model: Type[BaseModel],
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
    tools: Optional[list[LanguageModelTool]] = None,
    other_options: Optional[dict] = None,
    content_chunks: Optional[list[ContentChunk]] = None,
    structured_output_model: Optional[Type[BaseModel]] = None,
    structured_output_enforce_schema: bool = False,
) -> tuple[dict, str, dict, Optional[dict]]:
    """
    Prepares common parameters for completion requests.

    Returns:
        tuple containing:
        - options (dict): Combined options including tools and temperature
        - model (str): Resolved model name
        - messages_dict (dict): Processed messages
        - search_context (Optional[dict]): Processed content chunks if provided
    """

    options = _add_tools_to_options({}, tools)
    if structured_output_model:
        options = _add_response_format_to_options(
            options, structured_output_model, structured_output_enforce_schema
        )
    options["temperature"] = temperature
    if other_options:
        options.update(other_options)

    model = model_name.name if isinstance(model_name, LanguageModelName) else model_name

    # Different methods need different message dump parameters
    messages_dict = messages.model_dump(
        exclude_none=True,
        by_alias=content_chunks is not None,  # Use by_alias for streaming methods
    )

    search_context = (
        _to_search_context(content_chunks) if content_chunks is not None else None
    )

    return options, model, messages_dict, search_context
