# This tutorial shows how to get access to the open ai client through the unique
# plattform and how to use the responses endpoint
# %%
# Setup
from pathlib import Path

from unique_toolkit.framework_utilities.openai.client import get_openai_client

env_file = Path(__file__).parent.parent.parent / ".env"
client = get_openai_client(env_file=env_file)
model = "AZURE_o3_2025_0416"

# %%
# Simple response

response = client.responses.create(
    model=model,
    input="Tell me a three sentence bedtime story about a unicorn.",
)
print(response)
