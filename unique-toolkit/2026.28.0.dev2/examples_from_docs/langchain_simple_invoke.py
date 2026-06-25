# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit[langchain]>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///

# %%

from langchain_core.messages import HumanMessage, SystemMessage

from unique_toolkit import get_langchain_client

# Client uses UniqueSettings.from_env_auto() when unique_settings is omitted
llm = get_langchain_client()

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Write a one-sentence bedtime story about a unicorn."),
]

response = llm.invoke(messages)
print(response.content)
