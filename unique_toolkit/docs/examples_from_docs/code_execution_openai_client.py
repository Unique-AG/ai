# API Based example for code execution



# %%
# Unique Settings

from pathlib import Path
from unique_toolkit.app.unique_settings import UniqueSettings
unique_settings = UniqueSettings.from_env(env_file=Path("qa.env"))
unique_settings.init_sdk()

import unique_sdk
unique_sdk.api_base


# %%
# OpenAI Client

from unique_toolkit.framework_utilities.openai.client import get_openai_client
client = get_openai_client(unique_settings=unique_settings)


# %%
# Define tools for code execution
code_interpreter_tool = {"container": {"type": "auto"}, "type": "code_interpreter"}
    


# %%
# LLM call with a tool for code execution
from unique_toolkit.framework_utilities.openai.message_builder import OpenAIMessageBuilder

messages = "Use code to print hello world."


# %%
from unique_toolkit.language_model import LanguageModelName
response_with_code = client.responses.create(
    model=LanguageModelName.AZURE_GPT_5_2025_0807,
    tools=[code_interpreter_tool],
    input=messages,
)
# %%
response_with_code.output[1].outputs
# %%

# To include the output of the code generated in the response, you do the following:

response_with_output = client.responses.create(
    model=LanguageModelName.AZURE_GPT_5_2025_0807,
    tools=[code_interpreter_tool],
    input=messages,
    include=["code_interpreter_call.outputs"],
)
response_with_output.output
# %%
response_with_output.output[1].outputs
# %%
