# %%

from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from openai_compatible.settings import (
    get_default_headers,
)
from pydantic import BaseModel, Field

from unique_toolkit.app.unique_settings import UniqueSettings

env_file = Path(__file__).parent.parent / ".env"
settings = UniqueSettings.from_env(env_file=env_file)


llm = ChatOpenAI(
    base_url=settings.app.base_url + "/openai-proxy/",
    default_headers=get_default_headers(settings.app, settings.auth),
    model="AZURE_GPT_4o_2024_0806",
    api_key=settings.app.key,
)
response = llm.invoke("What is the capital of France?")

response.content


# %% Structured output directly


class ResponseFormatter(BaseModel):
    """Always use this tool to structure your response to the user."""

    answer: str = Field(description="The answer to the user's question")
    followup_question: str = Field(description="A followup question the user could ask")


model_with_structure = llm.with_structured_output(ResponseFormatter)
structured_output = model_with_structure.invoke("What is the powerhouse of the cell?")
structured_output

# %% ToolCalling


@tool
def add(a: int, b: int) -> int:
    """Adds a and b."""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiplies a and b."""
    return a * b


tools = [add, multiply]
llm_with_tools = llm.bind_tools(tools)


messages: list[BaseMessage] = [HumanMessage("What is 3 * 12? Also, what is 11 + 49?")]
ai_msg = AIMessage(**llm_with_tools.invoke(messages).model_dump())

messages.append(ai_msg)
for tool_call in ai_msg.tool_calls:
    selected_tool = {"add": add, "multiply": multiply}[tool_call["name"].lower()]
    tool_msg = selected_tool.invoke(tool_call)
    messages.append(tool_msg)

llm_with_tools.invoke(messages).content


# %%
