# ~/~ begin <<docs/plattforms/langchain/langchain.md#docs/.python_files/langchain_simple_invoke.py>>[init]
# ~/~ begin <<docs/setup/_script_dependencies_langchain.md#example-script-deps-langchain>>[init]
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unique-toolkit[langchain]>=2026.22.0",
#   "unique-sdk>=2026.22.0",
# ]
# ///
# ~/~ end

# ~/~ begin <<docs/plattforms/langchain/langchain.md#langchain_basic_invoke>>[init]
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
# ~/~ end
# ~/~ end
