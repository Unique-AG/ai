from enum import StrEnum
from typing import Any, Callable

import tiktoken
from pydantic import BaseModel


class OpenAIModelName(StrEnum):
    GPT_3_5_TURBO_0125 = "gpt-3.5-turbo-0125"
    GPT_4_0314 = "gpt-4-0314"
    GPT_4_32K_0314 = "gpt-4-32k-0314"
    GPT_4_0613 = "gpt-4-0613"
    GPT_4_32K_0613 = "gpt-4-32k-0613"
    GPT_4O_MINI_2024_07_18 = "gpt-4o-mini-2024-07-18"
    GPT_4O_2024_08_06 = "gpt-4o-2024-08-06"

class SpecialToolCallingTokens(BaseModel):
    func_init: int = 0
    prop_init: int = 0
    prop_key: int = 0
    enum_init: int = 0
    enum_item: int = 0
    func_end: int = 0

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

def num_tokens_from_messages(messages: list[dict[str,str]], encode: Callable[[str], list[int]] ) -> int:
    """Return the number of tokens used by a list of messages."""
    
    num_tokens = 0
    for message in messages:
        num_tokens += 3 # extra_tokens_per_message
        for key, value in message.items():
            num_tokens += len(encode(value))
            if key == "name":
                num_tokens +=  1 #extra_tokens_per_name
    num_tokens += 3

    return num_tokens

def get_special_token(model: OpenAIModelName) -> SpecialToolCallingTokens:

    special_token = SpecialToolCallingTokens()

    if model in [OpenAIModelName.GPT_4O_2024_08_06, OpenAIModelName.GPT_4O_MINI_2024_07_18]:
        # Set function settings for the above models
        special_token.func_init=7
        special_token.prop_init=3
        special_token.prop_key=3
        special_token.enum_init=-3
        special_token.enum_item=3
        special_token.func_end=12
        
    elif model in [
        OpenAIModelName.GPT_3_5_TURBO_0125,
        OpenAIModelName.GPT_4_0314,
        OpenAIModelName.GPT_4_0613,
        OpenAIModelName.GPT_4_32K_0314,
        OpenAIModelName.GPT_4_32K_0613,
    ]:
        # Set function settings for the above models
        special_token.func_init=10
        special_token.prop_init=3
        special_token.prop_key=3
        special_token.enum_init=-3
        special_token.enum_item=3
        special_token.func_end=12
    else:
        raise NotImplementedError(
            f"""num_tokens_for_tools() is not implemented for model {model}."""
        )
    return special_token

def num_tokens_for_tools(functions:list[dict[str,Any]], special_token: SpecialToolCallingTokens, encode: Callable[[str], list[int]]):

    def num_token_function_enum(properties: dict[str, Any], encode: Callable[[str], list[int]]):
        
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
            func_token_count += len(encode(function.get("name","") + ":" + function.get("description","").rstrip(".").rstrip()))
            if len(function.get("parameters",{}).get("properties","")) > 0:
                properties = function.get("parameters",{}).get("properties","")
                func_token_count += special_token.prop_init
                
                for key in list(properties.keys()):
                    func_token_count += special_token.prop_key
                    
                    if "enum" in properties[key].keys():
                        func_token_count += num_token_function_enum(properties, encode)                        
                    
                    func_token_count += len(encode(f"{key}:{properties[key]['type']}:{properties[key]['description'].rstrip('.').rstrip()}"))
        
        func_token_count += special_token.func_end
        
    return func_token_count 


if __name__ == "__main__":
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

    model_str = ["gpt-3.5-turbo", "gpt-4-0613", "gpt-4", "gpt-4o", "gpt-4o-mini"]
    token_counts = [129, 129, 129, 124, 124]
    for num, model in zip(token_counts, model_str):
        encoder = get_encoder(model_str=model)
        assert num == num_tokens_from_messages(example_messages, encode=encoder.encode)

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
        tool_token_count = num_tokens_for_tools(functions, special_token, encoder.encode)
        message_token_count = num_tokens_from_messages(example_messages, encoder.encode)
        
        print(encoder.name, num, tool_token_count+message_token_count , model)
        assert num == tool_token_count + message_token_count