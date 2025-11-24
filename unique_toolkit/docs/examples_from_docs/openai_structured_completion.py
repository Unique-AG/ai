# %%
from pydantic import BaseModel

from unique_toolkit import (
    LanguageModelName,
)
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)

model = LanguageModelName.AZURE_GPT_4o_2024_1120
client = get_openai_client()

messages = (
    OpenAIMessageBuilder()
    .system_message_append(content="You are a helpful assistant")
    .user_message_append(content="Hi Andy, how are you?", name="JohnDoe")
    .user_message_append(content="Thanks John, I'm doing great! How about our strategy meeting", name="AndyTurner")
    .user_message_append(content="Yes, let's meet at 10am on the 22nd of December", name="JohnDoe")
    .user_message_append(content="That's not working for me! How about 11am?", name="AndyTurner")
    .user_message_append(content="That's perfect! I'll see you there!", name="JohnDoe")
).messages

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]


completion = client.beta.chat.completions.parse(
    model=model,
    messages=messages,
    response_format=CalendarEvent,
)
print(completion.choices[0].message.content)
