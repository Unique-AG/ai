# %%
# Code execution with auto-managed container (Responses API)

from openai.types.responses.tool_param import CodeInterpreter
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.language_model import LanguageModelName

model_name = LanguageModelName.AZURE_GPT_5_2025_0807
client = get_openai_client()

# %%
# Define tool and call Responses API
code_interpreter_tool = CodeInterpreter(type="code_interpreter", container={"type": "auto"})
messages = "Use code to print hello world."

response_with_output = client.responses.create(
    model=model_name,
    tools=[code_interpreter_tool],
    input=messages,
    include=["code_interpreter_call.outputs"],
)

# %%
# response.output is a list (e.g. text block, then code_interpreter_call)
print(response_with_output.output)
print(response_with_output.output[1].outputs)  # type: ignore[union-attr]
