# This tutorial shows how to get access to the open ai client through the unique
# plattform and how to use the chat completions endpoint

# %%
# Setup
from pathlib import Path

from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
from pydantic import BaseModel

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)

env_file = Path(__file__).parent.parent.parent / ".env"
unique_settings = UniqueSettings.from_env(env_file=env_file)
client = get_openai_client(unique_settings)
model = "AZURE_GPT_4o_2024_0806"


messages = (
    OpenAIMessageBuilder()
    .system_message_append(content="You are a helpful assistant")
    .user_message_append(content="How is the weather in New York")
).messages

# %%
# Simple Completion

response = client.chat.completions.create(
    messages=messages,
    model=model,
)

for stuff in response:
    print(stuff)

# %%
# Structured Output


class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]


completion = client.beta.chat.completions.parse(
    model=model,
    messages=messages,
    response_format=CalendarEvent,
)
completion.choices[0].message.content

# %%
## Function calling
weather_tool_description = ChatCompletionToolParam(
    function=FunctionDefinition(
        name="get_weather",
        description="Get current temperature for a given location.",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia",
                },
            },
            "required": [
                "location",
            ],
            "additionalProperties": False,
        },
        strict=True,
    ),
    type="function",
)

completion = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "What is the weather like in Paris today?"}],
    tools=[weather_tool_description],
)

# %%
# Developer Message and logprops
completion = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "developer", "content": "Always answer in french"},
        {"role": "user", "content": "What is the weather like in Paris today?"},
    ],
    logprobs=True,
)


print(completion.choices[0].message.content)


# %%
# Using Logprobs
completion = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "developer", "content": "Always answer in french"},
        {"role": "user", "content": "What is the weather like in Paris today?"},
    ],
    logprobs=True,
)

print(completion.choices[0].message.content)

# %%
