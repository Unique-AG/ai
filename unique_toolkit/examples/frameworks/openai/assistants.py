# This tutorial shows how to get access to the open ai client through the unique
# plattform and how to use the assistant endpoint

# %%
from pathlib import Path

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client

env_file = Path(__file__).parent.parent.parent / ".env"
unique_settings = UniqueSettings.from_env(env_file=env_file)
client = get_openai_client(unique_settings)
model = "AZURE_GPT_4o_2024_0806"

# Set custom headers required by your API
extra_headers = {
    "x-model": model,
}

messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "How is the weather in New York"},
]


assistant = client.beta.assistants.create(
    name="My Assistant",
    model=model,
    instructions="You are a personal math tutor. When asked a question, write and run Python code to solve it. If the question is not related to math, politely decline to answer.",
    tools=[
        {
            "type": "code_interpreter",
        },
    ],
)

thread = client.beta.threads.create(
    extra_headers=extra_headers,
)

print(f"Created assistant: {assistant.id}")
print(f"Created thread: {thread.id}")

client.beta.threads.messages.create(
    extra_headers=extra_headers,
    thread_id=thread.id,
    content="I need to solve the equation 3x + 4 - 10 = 24",
    role="user",
)

run = client.beta.threads.runs.create(
    extra_headers=extra_headers,
    model=model,
    thread_id=thread.id,
    assistant_id=assistant.id,
)

print(f"Created run: {run.id}")

while run.status not in ["completed", "failed"]:
    run = client.beta.threads.runs.retrieve(
        extra_headers=extra_headers,
        thread_id=thread.id,
        run_id=run.id,
    )
    print(f"Run status: {run.status}")

messages = client.beta.threads.messages.list(
    extra_headers=extra_headers,
    thread_id=thread.id,
)

print(messages)

# %%
