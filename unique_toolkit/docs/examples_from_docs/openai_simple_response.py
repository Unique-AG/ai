# %%
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
    .user_message_append(content="How is the weather in New York")
).messages

response = client.responses.create(
    model=model, input="Write a one-sentence bedtime story about a unicorn."
)
