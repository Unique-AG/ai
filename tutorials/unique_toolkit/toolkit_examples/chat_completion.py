# %%

from pathlib import Path

from pydantic import BaseModel, Field
from utilities_examples.init_sdk import init_from_env_file

import unique_toolkit.language_model.functions as llm_functions
from unique_toolkit import LanguageModelMessages
from unique_toolkit.language_model import (
    LanguageModelName,
    LanguageModelToolDescription,
)

company_id, _ = init_from_env_file(Path(__file__).parent / ".." / ".env")

# %%

## Simple chat completion

messages = (
    LanguageModelMessages([])
    .builder()
    .system_message_append("You are a helpful assistant")
    .user_message_append("What is the capital of France?")
    .build()
)


response = llm_functions.complete(
    company_id=company_id,
    model_name=LanguageModelName.AZURE_GPT_4o_2024_0806,  # Make sure this is deployed in your environment
    messages=messages,
)


print(response.choices[0].message.content)
# %%


## Chat completion with tools


class WeatherParameters(BaseModel):
    location: str = Field(description="The location to get the weather for")
    date: str = Field(description="The date to get the weather for")


weather_tool = LanguageModelToolDescription(
    name="weather",
    description="Get the weather in a in Paris tomorrow",
    parameters=WeatherParameters,
)

messages = (
    LanguageModelMessages([])
    .builder()
    .system_message_append("You are a helpful assistant")
    .user_message_append("What is the weather in Paris tomorrow?")
    .build()
)

response = llm_functions.complete(
    company_id=company_id,
    model_name=LanguageModelName.AZURE_GPT_4o_2024_0806,  # Make sure this is deployed in your environment
    messages=messages,
    tools=[weather_tool],
)


# %%
tool_calls = response.choices[0].message.tool_calls

if tool_calls:
    for tool_call in tool_calls:
        print(f"Tool name: {tool_call.function.name}")
        print(f"Tool args: {tool_call.function.arguments}")
