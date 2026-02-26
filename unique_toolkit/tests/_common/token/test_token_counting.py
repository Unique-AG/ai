# Original source
# https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb

from pathlib import Path

import pytest
import tiktoken
from PIL import Image

from unique_toolkit._common.token.token_counting import (
    SpecialToolCallingTokens,
    count_tokens,
    num_tokens_for_tools,
    num_tokens_from_messages,
)
from unique_toolkit._common.utils.image.encode import image_to_base64
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

CURRENT_DIR = Path(__file__).parent.absolute()


def get_model_name(model: str) -> LanguageModelName:
    try:
        return LanguageModelName(model)
    except ValueError:
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


def get_special_token(model: LanguageModelName) -> SpecialToolCallingTokens:
    special_token = SpecialToolCallingTokens()

    if model in [
        LanguageModelName.AZURE_GPT_4o_2024_0806,
        LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
    ]:
        # Set function settings for the above models
        special_token.func_init = 7
        special_token.prop_init = 3
        special_token.prop_key = 3
        special_token.enum_init = -3
        special_token.enum_item = 3
        special_token.func_end = 12

    elif model in [
        LanguageModelName.AZURE_GPT_35_TURBO_0125,
        LanguageModelName.AZURE_GPT_4_0613,
        LanguageModelName.AZURE_GPT_4_32K_0613,
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
        "AZURE_GPT_35_TURBO_0125",
        "AZURE_GPT_4_0613",
        "AZURE_GPT_4_32K_0613",
        "AZURE_GPT_4o_MINI_2024_0718",
        "AZURE_GPT_4o_2024_0806",
    ]
    expected_token_counts = [124, 124, 124, 124, 124]

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

    model_str_list = [
        "AZURE_GPT_35_TURBO_0125",
        "AZURE_GPT_4_0613",
        "AZURE_GPT_4o_2024_0806",
        "AZURE_GPT_4o_MINI_2024_0718",
    ]
    token_counts = [104, 104, 101, 101]

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
    model_str = "AZURE_GPT_4o_2024_0806"
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


@pytest.mark.ai
class TestCountTokens:
    def test_count_with_model(self):
        model = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_0513)
        count = count_tokens("Hello world", model)

        assert isinstance(count, int)
        assert count > 0

    def test_count_without_model(self):
        count = count_tokens("Hello world", model=None)

        assert isinstance(count, int)
        assert count > 0

        expected = len(tiktoken.get_encoding("cl100k_base").encode("Hello world"))
        assert count == expected

    def test_count_empty_string(self):
        model = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_0513)
        assert count_tokens("", model) == 0
        assert count_tokens("", None) == 0

    def test_count_qwen_model(self):
        model = LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)
        count = count_tokens("Hello world", model)

        assert isinstance(count, int)
        assert count > 0

    def test_count_deepseek_model(self):
        model = LanguageModelInfo.from_name(LanguageModelName.LITELLM_DEEPSEEK_V3)
        count = count_tokens("Hello world", model)

        assert isinstance(count, int)
        assert count > 0

    def test_qwen_vs_gpt_different_counts(self):
        qwen = LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)
        gpt = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_0513)

        text = "这是一个测试文本，用于验证不同的分词器会产生不同的结果。"
        qwen_count = count_tokens(text, qwen)
        gpt_count = count_tokens(text, gpt)

        assert qwen_count != gpt_count
