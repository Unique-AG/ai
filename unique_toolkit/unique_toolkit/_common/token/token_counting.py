# Original source
# https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any, Callable, get_args

import tiktoken
from openai.types.responses import ResponseOutputItem
from pydantic import BaseModel

from unique_toolkit._common.token.image_token_counting import (
    calculate_image_tokens_from_base64,
)
from unique_toolkit.language_model import (
    LanguageModelMessage,
    LanguageModelMessages,
    LanguageModelName,
)

if TYPE_CHECKING:
    from unique_toolkit.language_model.infos import LanguageModelInfo

DEFAULT_ENCODING = os.getenv("UNIQUE_DEFAULT_TOKENIZER_ENCODING", "cl100k_base")

# Extract concrete types from ResponseOutputItem Union for isinstance checks
# ResponseOutputItem is Annotated[Union[...], PropertyInfo]
_RESPONSE_OUTPUT_TYPES = get_args(get_args(ResponseOutputItem)[0])


class SpecialToolCallingTokens(BaseModel):
    func_init: int = 0
    prop_init: int = 0
    prop_key: int = 0
    enum_init: int = 0
    enum_item: int = 0
    func_end: int = 0


def get_special_token(model: LanguageModelName) -> SpecialToolCallingTokens:
    special_token = SpecialToolCallingTokens()

    match model:
        case (
            LanguageModelName.AZURE_GPT_4o_2024_0513
            | LanguageModelName.AZURE_GPT_4o_2024_0806
            | LanguageModelName.AZURE_GPT_4o_MINI_2024_0718
            | LanguageModelName.AZURE_GPT_4o_2024_1120
        ):
            special_token.func_init = 7
            special_token.prop_init = 3
            special_token.prop_key = 3
            special_token.enum_init = -3
            special_token.enum_item = 3
            special_token.func_end = 12

        case (
            LanguageModelName.AZURE_GPT_35_TURBO_0125
            | LanguageModelName.AZURE_GPT_4_0613
            | LanguageModelName.AZURE_GPT_4_32K_0613
            | LanguageModelName.AZURE_GPT_4_TURBO_2024_0409
        ):
            special_token.func_init = 10
            special_token.prop_init = 3
            special_token.prop_key = 3
            special_token.enum_init = -3
            special_token.enum_item = 3
            special_token.func_end = 12

        case _:
            raise NotImplementedError(
                f"""num_tokens_for_tools() is not implemented for model {model}."""
            )
    return special_token


def num_tokens_per_messages(
    messages: list[dict[str, str]], encode: Callable[[str], list[int]]
) -> list[int]:
    """Return the number of tokens used by a list of messages."""

    num_token_per_message = []
    for message in messages:
        num_tokens = 3  # extra_tokens_per_message
        for key, value in message.items():
            if key == "content":
                if message.get("role") == "tool":
                    """
                    We have observed a general difference in the way tool response messages are handled.
                    Specifically, if we take a list of tool responses and artificially transform them into user messages (content field stays the same)
                    the token consumption goes does drastically, this seems to scale with the number of tokens in the tool responses.

                    the json.dumps() method was found by trial and error. It will give a conservative estimate, but seems to be close to the token count
                    returned from the openai call.
                    """
                    num_tokens += len(encode(json.dumps(value)))
                elif isinstance(value, list):
                    # NOTE: The result returned by the function below is not 100% accurate.
                    num_tokens += handle_message_with_images(value, encode)
                else:
                    num_tokens += len(encode(value))
            elif isinstance(value, str):
                num_tokens += len(encode(value))

            if key == "name":
                num_tokens += 1  # extra_tokens_per_name

        num_token_per_message.append(num_tokens)

    return num_token_per_message


def num_tokens_from_messages(
    messages: list[dict[str, str]], encode: Callable[[str], list[int]]
) -> int:
    """Return the number of tokens used by a list of messages."""

    num_tokens_per_message = num_tokens_per_messages(messages, encode)
    num_tokens = sum(num_tokens_per_message) + 3

    return num_tokens


def num_tokens_for_tools(
    functions: list[dict[str, Any]],
    special_token: SpecialToolCallingTokens,
    encode: Callable[[str], list[int]],
):
    def num_token_function_enum(
        properties: dict[str, Any], encode: Callable[[str], list[int]]
    ):
        enum_token_count = 0
        enum_token_count += special_token.enum_init
        for item in properties[key]["enum"]:
            enum_token_count += special_token.enum_item
            enum_token_count += len(encode(item))

        return enum_token_count

    func_token_count = 0
    if len(functions) > 0:
        for func in functions:
            func_token_count += special_token.func_init
            function = func.get("function", {})
            func_token_count += len(
                encode(
                    function.get("name", "")
                    + ":"
                    + function.get("description", "").rstrip(".").rstrip()
                )
            )
            if len(function.get("parameters", {}).get("properties", "")) > 0:
                properties = function.get("parameters", {}).get("properties", "")
                func_token_count += special_token.prop_init

                for key in list(properties.keys()):
                    func_token_count += special_token.prop_key

                    if "enum" in properties[key].keys():
                        func_token_count += num_token_function_enum(properties, encode)

                    func_token_count += len(
                        encode(
                            f"{key}:{properties[key]['type']}:{properties[key]['description'].rstrip('.').rstrip()}"
                        )
                    )

        func_token_count += special_token.func_end

    return func_token_count


def handle_message_with_images(message: list[dict], encode: Callable[[str], list[int]]):
    token_count = 0
    for item in message:
        if item.get("type") == "image_url":
            image_url = item.get("imageUrl", {}).get("url")
            if image_url:
                token_count += calculate_image_tokens_from_base64(image_url)
        elif item.get("type") == "text":
            token_count += len(encode(item.get("text", "")))
    return token_count


def messages_to_openai_messages(
    messages: LanguageModelMessages | list[LanguageModelMessage],
):
    if isinstance(messages, list):
        messages = LanguageModelMessages(messages)  # type: ignore[arg-type]

    return [
        {
            k: v
            for k, v in m.items()
            if (
                k in ["content", "role", "name"] and v is not None
            )  # Ignore tool_calls for now
        }
        for m in messages.model_dump(mode="json")
    ]


def num_tokens_per_language_model_message(
    messages: LanguageModelMessages | list[LanguageModelMessage],
    encode: Callable[[str], list[int]],
) -> list[int]:
    return num_tokens_per_messages(
        messages=messages_to_openai_messages(messages), encode=encode
    )


def num_token_for_language_model_messages(
    messages: LanguageModelMessages | list[LanguageModelMessage],
    encode: Callable[[str], list[int]],
) -> int:
    """
    Count tokens for language model messages.

    Supports both LanguageModelMessage (standard Completions API messages)
    and ResponseOutputItem (Responses API output items). For ResponseOutputItem,
    tokens are estimated via JSON serialization.
    """
    # Handle LanguageModelMessages wrapper with mixed types
    if isinstance(messages, LanguageModelMessages):
        # Check if any ResponseOutputItem instances present
        has_response_items = any(
            isinstance(item, _RESPONSE_OUTPUT_TYPES) for item in messages.root
        )

        if has_response_items:
            # Count mixed types individually
            token_count = 0
            for item in messages.root:
                if isinstance(item, _RESPONSE_OUTPUT_TYPES):
                    # ResponseOutputItem: estimate via JSON serialization
                    json_str = json.dumps(item.model_dump(exclude_defaults=True))
                    token_count += len(encode(json_str))
                else:
                    # LanguageModelMessage: recursive call with single item
                    token_count += num_token_for_language_model_messages([item], encode)  # type: ignore[list-item]
            return token_count

    # Standard path: all LanguageModelMessage items
    return num_tokens_from_messages(messages_to_openai_messages(messages), encode)


def count_tokens(text: str, model: LanguageModelInfo | None = None) -> int:
    """Count tokens for a text string using the model's tokenizer."""
    if not text:
        return 0

    if model is None:
        encoder = tiktoken.get_encoding(DEFAULT_ENCODING)
        return len(encoder.encode(text))

    return len(model.get_encoder()(text))
