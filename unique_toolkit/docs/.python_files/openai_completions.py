# ~/~ begin <<docs/plattforms/openai/openai.md#docs/.python_files/openai_completions.py>>[init]
# ~/~ begin <<docs/plattforms/openai/openai.md#common_library_imports>>[init]
from pathlib import Path
from pydantic import BaseModel
# ~/~ end
# ~/~ begin <<docs/modules/examples/chat/chat_service.md#default_language_model>>[init]
from unique_toolkit import LanguageModelName

model_name = LanguageModelName.AZURE_GPT_4o_2024_1120
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#openai_type_imports>>[init]
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#openai_toolkit_imports>>[init]
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#openai_chat_completion_client_imports>>[init]
settings = UniqueSettings.from_env_auto()
client = get_openai_client(unique_settings=settings)
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#openai_chat_completion_messages>>[init]


messages = (
    OpenAIMessageBuilder()
    .system_message_append(content="You are a helpful assistant")
    .user_message_append(content="How is the weather in New York")
).messages
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#openai_chat_completion_simple_completion>>[init]
# Simple Completion
response = client.chat.completions.create(
    messages=messages,
    model=model_name,
)
for c in response:
    print(c)
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#openai_chat_completion_structured_output>>[init]


class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]


completion = client.beta.chat.completions.parse(
    model=model_name,
    messages=messages,
    response_format=CalendarEvent,
)
completion.choices[0].message.content
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#openai_chat_completion_function_calling>>[init]
from pydantic import Field
from unique_toolkit import LanguageModelToolDescription

class WeatherParameters(BaseModel):
    model_config = {"extra": "forbid"}
    location: str = Field(description="City and country e.g. Bogotá, Colombia")

weather_tool_description = LanguageModelToolDescription(
    name="get_weather",
    description="Get current temperature for a given location.",
    parameters=WeatherParameters,
    strict=True,
)

weather_tool_description_toolkit= weather_tool_description.to_openai()

messages = (
    OpenAIMessageBuilder()
    .system_message_append(content="You are a helpful assistant")
    .user_message_append(content="What is the weather like in Paris today?")
).messages

completion = client.chat.completions.create(
    model=model_name,
    messages=messages,
    tools=[weather_tool_description_toolkit],
)

completion.choices[0].message.tool_calls
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#openai_chat_completion_developer_message>>[init]

messages = (
    OpenAIMessageBuilder()
    .system_message_append(content="You are a helpful assistant")
    .user_message_append(content="How is the weather in New York")
).messages

completion = client.chat.completions.create(
    model=model_name,
    messages=messages,
)
print(completion.choices[0].message.content)
# ~/~ end
# ~/~ end
