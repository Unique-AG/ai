# %%
from pydantic import BaseModel, Field

from unique_toolkit import (
    LanguageModelName,
    LanguageModelToolDescription,
)
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)

model = LanguageModelName.AZURE_GPT_4o_2024_1120
client = get_openai_client()


class WeatherParameters(BaseModel):
    model_config = {"extra": "forbid"}
    location: str = Field(description="City and country e.g. Bogotá, Colombia")


weather_tool_description = LanguageModelToolDescription(
    name="get_weather",
    description="Get current temperature for a given location.",
    parameters=WeatherParameters,
    strict=True,
)

weather_tool_description_toolkit = weather_tool_description.to_openai()
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
