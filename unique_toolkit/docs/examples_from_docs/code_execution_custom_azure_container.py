# %%
# Custom Azure Container

from unique_toolkit.app.unique_settings import UniqueSettings
from pathlib import Path
unique_settings = UniqueSettings.from_env(env_file=Path("qa.env"))
unique_settings.init_sdk()

import unique_sdk
unique_sdk.api_base

# %%
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.language_model import LanguageModelName

model_name = LanguageModelName.AZURE_GPT_5_2025_0807

client = get_openai_client(unique_settings=unique_settings, 
                           additional_headers={"x-model": model_name} # NOTE: The client header used here should match the model used for code execution
                           ) 


# %%
    
# Create a custom Azure container
container = client.containers.create(
    name="code_execution_container", # Recommended to use chat_id
    expires_after={"anchor": "last_active_at", "minutes": 20},
)

# %%
print(f"Created container: {container.id}")

# Define tools for code execution
code_interpreter_tool = {"container": container.id, "type": "code_interpreter"}

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

print(f"Executed code output: {response_with_output.output[1].outputs}")

# %%

