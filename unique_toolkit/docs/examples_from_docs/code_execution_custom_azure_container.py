# %%
# Custom Azure Container


# %%
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.language_model import LanguageModelName

from openai.types.responses.tool_param import CodeInterpreter

model_name = LanguageModelName.AZURE_GPT_5_2025_0807

# NOTE: The client header used here should match the model used for code execution
client = get_openai_client(
                    additional_headers={"x-model": model_name} 
                ) 

# %%
    
# Create a custom Azure container
# Recommended to use chat_id in the name in order to differentiate between the containers created for the different chats
# Example
container = client.containers.create(
    name="code_execution_container", 
    # Control when container is cleaned
    expires_after={"anchor": "last_active_at", "minutes": 20}
)

# %%
print(f"Created container: {container.id}")

# Define tools for code execution (CodeInterpreter for type safety)
code_interpreter_tool = CodeInterpreter(type="code_interpreter", container=container.id)

# %%

messages = "Use code to print hello world."

# LLM call with a tool for code execution

response_with_output = client.responses.create(
    model=model_name, # Should match the model specified in the client header
    tools=[code_interpreter_tool],
    input=messages,
    include=["code_interpreter_call.outputs"],
)

print(f"Response: {response_with_output.output}")

print(f"Executed code output: {response_with_output.output[1].outputs}")  # type: ignore[union-attr]

# %%

