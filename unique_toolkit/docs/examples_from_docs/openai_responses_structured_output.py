# %%
from pydantic import BaseModel

from unique_toolkit import (
    LanguageModelName,
)
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    ResponseInputBuilder,
)

model = LanguageModelName.AZURE_GPT_4o_2024_1120
client = get_openai_client()

messages = (
    ResponseInputBuilder()
    .system_message_append(content="You are a helpful assistant")
    .user_message_append(content="How is the weather in New York")
).messages


class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]


response = client.responses.parse(
    model=model,
    input=messages,
    text_format=CalendarEvent,
)

print(response)
