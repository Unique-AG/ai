# Original source
# https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb

from enum import StrEnum
from pathlib import Path

import tiktoken
from PIL import Image

from unique_toolkit._common.token.token_counting import (
    SpecialToolCallingTokens,
    num_tokens_for_tools,
    num_tokens_from_messages,
)
from unique_toolkit._common.utils.image.encode import image_to_base64

CURRENT_DIR = Path(__file__).parent.absolute()


class OpenAIModelName(StrEnum):
    GPT_3_5_TURBO_0125 = "gpt-3.5-turbo-0125"
    GPT_4_0314 = "gpt-4-0314"
    GPT_4_32K_0314 = "gpt-4-32k-0314"
    GPT_4_0613 = "gpt-4-0613"
    GPT_4_32K_0613 = "gpt-4-32k-0613"
    GPT_4O_MINI_2024_07_18 = "gpt-4o-mini-2024-07-18"
    GPT_4O_2024_08_06 = "gpt-4o-2024-08-06"


def get_model_name(model: str) -> OpenAIModelName:
    if model in [
        "gpt-3.5-turbo-0125",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        "gpt-4o-mini-2024-07-18",
        "gpt-4o-2024-08-06",
    ]:
        return OpenAIModelName(model)
    elif "gpt-3.5-turbo" in model:
        return OpenAIModelName.GPT_3_5_TURBO_0125
    elif "gpt-4o-mini" in model:
        return OpenAIModelName.GPT_4O_MINI_2024_07_18
    elif "gpt-4o" in model:
        return OpenAIModelName.GPT_4O_2024_08_06
    elif "gpt-4" in model:
        return OpenAIModelName.GPT_4_0613
    else:
        raise NotImplementedError(
            f"""get_model_name() is not implemented for model {model}."""
        )


def get_encoder(model_str) -> tiktoken.Encoding:
    model = get_model_name(model_str)  # Use the new function to get the model

    try:
        encoding = tiktoken.encoding_for_model(model.value)
    except KeyError:
        print("Warning: model not found. Using o200k_base encoding.")
        encoding = tiktoken.get_encoding("o200k_base")

    return encoding


def get_special_token(model: OpenAIModelName) -> SpecialToolCallingTokens:
    special_token = SpecialToolCallingTokens()

    if model in [
        OpenAIModelName.GPT_4O_2024_08_06,
        OpenAIModelName.GPT_4O_MINI_2024_07_18,
    ]:
        # Set function settings for the above models
        special_token.func_init = 7
        special_token.prop_init = 3
        special_token.prop_key = 3
        special_token.enum_init = -3
        special_token.enum_item = 3
        special_token.func_end = 12

    elif model in [
        OpenAIModelName.GPT_3_5_TURBO_0125,
        OpenAIModelName.GPT_4_0314,
        OpenAIModelName.GPT_4_0613,
        OpenAIModelName.GPT_4_32K_0314,
        OpenAIModelName.GPT_4_32K_0613,
    ]:
        # Set function settings for the above models
        special_token.func_init = 10
        special_token.prop_init = 3
        special_token.prop_key = 3
        special_token.enum_init = -3
        special_token.enum_item = 3
        special_token.func_end = 12
    else:
        raise NotImplementedError(
            f"""num_tokens_for_tools() is not implemented for model {model}."""
        )
    return special_token


def test_num_tokens_from_messages():
    example_messages = [
        {
            "role": "system",
            "content": "You are a helpful, pattern-following assistant that translates corporate jargon into plain English.",
        },
        {
            "role": "system",
            "name": "example_user",
            "content": "New synergies will help drive top-line growth.",
        },
        {
            "role": "system",
            "name": "example_assistant",
            "content": "Things working well together will increase revenue.",
        },
        {
            "role": "system",
            "name": "example_user",
            "content": "Let's circle back when we have more bandwidth to touch base on opportunities for increased leverage.",
        },
        {
            "role": "system",
            "name": "example_assistant",
            "content": "Let's talk later when we're less busy about how to do better.",
        },
        {
            "role": "user",
            "content": "This late pivot means we don't have time to boil the ocean for the client deliverable.",
        },
    ]

    model_str_list = [
        "gpt-3.5-turbo-0125",
        "gpt-4-0613",
        "gpt-4-32k-0314",
        "gpt-4o-mini-2024-07-18",
        "gpt-4o-2024-08-06",
    ]
    expected_token_counts = [129, 129, 129, 124, 124]

    for model_str, expected_count in zip(model_str_list, expected_token_counts):
        encoder = get_encoder(model_str=model_str)
        assert (
            num_tokens_from_messages(example_messages, encode=encoder.encode)
            == expected_count
        )


def test_num_tokens_for_tools():
    functions = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {
                            "type": "string",
                            "description": "The unit of temperature to return",
                            "enum": ["celsius", "fahrenheit"],
                        },
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    example_messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that can answer to questions about the weather.",
        },
        {
            "role": "user",
            "content": "What's the weather like in San Francisco?",
        },
    ]

    model_str_list = ["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini"]
    token_counts = [105, 105, 101, 101]

    for num, model_str in zip(token_counts, model_str_list):
        model = get_model_name(model_str)  # Use the new function to get the model
        special_token = get_special_token(model)

        encoder = get_encoder(model_str=model_str)
        tool_token_count = num_tokens_for_tools(
            functions, special_token, encoder.encode
        )
        message_token_count = num_tokens_from_messages(example_messages, encoder.encode)

        print(encoder.name, num, tool_token_count + message_token_count, model)
        assert num == tool_token_count + message_token_count


def test_token_counting_with_image():
    image_path_1 = CURRENT_DIR / "example_images/image1.jpg"
    image_path_2 = CURRENT_DIR / "example_images/image2.jpg"
    with Image.open(image_path_1) as img:
        base64_image_1 = image_to_base64(img)
    with Image.open(image_path_2) as img:
        base64_image_2 = image_to_base64(img)
    example_messages_1 = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "This late pivot means we don't have time to boil the ocean for the client deliverable.",
                },
                {"type": "image_url", "imageUrl": {"url": base64_image_1}},
            ],
        }
    ]

    example_messages_2 = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "This late pivot means we don't have time to boil the ocean for the client deliverable.",
                },
                {"type": "image_url", "imageUrl": {"url": base64_image_2}},
            ],
        }
    ]

    # Test with a small image (low detail)
    model_str = "gpt-4o-2024-08-06"
    encoder = get_encoder(model_str)

    message_token_count_1 = num_tokens_from_messages(example_messages_1, encoder.encode)
    message_token_count_2 = num_tokens_from_messages(example_messages_2, encoder.encode)

    # # NOTE: As explained in the documentation, the function overestimates the number of tokens consumed by the model
    # in comment, you can find the actual number of tokens consumed when the request is sent to the llm.
    assert message_token_count_1 == 790  # 652
    assert message_token_count_2 == 1130  # 964

    example_messages = [
        {
            "role": "system",
            "content": "You are a helpful, pattern-following assistant that translates corporate jargon into plain English.",
        },
        {
            "role": "user",
            "content": "New synergies will help drive top-line growth.",
        },
        {
            "role": "assistant",
            "content": "Things working well together will increase revenue.",
        },
        {
            "role": "user",
            "content": "Let's circle back when we have more bandwidth to touch base on opportunities for increased leverage.",
        },
        {
            "role": "assistant",
            "content": "Let's talk later when we're less busy about how to do better.",
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "This late pivot means we don't have time to boil the ocean for the client deliverable.",
                },
                {"type": "image_url", "imageUrl": {"url": base64_image_1}},
                {"type": "image_url", "imageUrl": {"url": base64_image_2}},
            ],
        },
    ]

    message_token_count = num_tokens_from_messages(example_messages, encoder.encode)

    assert (
        message_token_count == 1980
    )  # 1676 NOTE: This is the actual result when sending the request to openai
