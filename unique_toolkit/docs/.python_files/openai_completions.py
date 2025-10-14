# ~/~ begin <<docs/plattforms/openai/openai.md#docs/.python_files/openai_completions.py>>[init]
# ~/~ begin <<docs/setup/_common_imports.md#common_imports>>[init]
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent 
from unique_toolkit import ChatService, ContentService, EmbeddingService, LanguageModelService, LanguageModelName, KnowledgeBaseService
from unique_toolkit.chat.schemas import ChatMessageAssessmentStatus, ChatMessageAssessmentType, ChatMessageAssessmentLabel
import os
import io
import tempfile
import requests
from pathlib import Path
from unique_toolkit.content.schemas import ContentSearchType, ContentRerankerConfig, ContentChunk, ContentReference
import unique_sdk
from pydantic import BaseModel, Field
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
from pydantic import Field
from unique_toolkit import LanguageModelToolDescription
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#toolkit_language_model>>[init]
model = LanguageModelName.AZURE_GPT_4o_2024_1120
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#get_openai_client>>[init]
client = get_openai_client()
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
    model=model,
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
    model=model,
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
    model=model,
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
    model=model,
    messages=messages,
)
print(completion.choices[0].message.content)
# ~/~ end
# ~/~ end
