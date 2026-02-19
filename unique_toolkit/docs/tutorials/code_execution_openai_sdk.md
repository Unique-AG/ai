# Code Execution with the OpenAI SDK

This tutorial shows how to use the OpenAI SDK to run code in a sandbox via the **Responses API** (`client.responses.create`). Code execution lets the model run Python for tasks like data analysis, plotting, or file processing. It is only available through the Responses API, not Chat Completions.

## What You'll Learn

- Using an auto-managed container for code execution (quick start)
- Including code outputs (stdout, stderr, results) in the response
- Creating and using a custom Azure container for per-chat isolation and lifecycle control
- Uploading and downloading files from containers
- Checking if a container or file exists before reusing or re-uploading

## Prerequisites

- `unique_toolkit` and the OpenAI SDK
- A model that supports code execution (e.g. `LanguageModelName.AZURE_GPT_5_2025_0807`)

For general client setup, see [OpenAI Client](../plattforms/openai/openai.md).

---

## 1. Quick start: auto-managed container

Get a client, define the code interpreter tool with `container={"type": "auto"}`, and call the Responses API. The API manages the container for you.

```python
from openai.types.responses.tool_param import CodeInterpreter
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.language_model import LanguageModelName

model_name = LanguageModelName.AZURE_GPT_5_2025_0807
client = get_openai_client()

code_interpreter_tool = CodeInterpreter(type="code_interpreter", container={"type": "auto"})

response = client.responses.create(
    model=model_name,
    tools=[code_interpreter_tool],
    input="Use code to print hello world.",
)

# response.output is a list; the first item is typically the text reply
print(response.output)
```

---

## 2. Including code outputs

To get stdout, stderr, or execution results from the run code, pass `include=["code_interpreter_call.outputs"]`. The `response.output` list will contain both the text block and the code interpreter call with `.outputs`.

```python
response_with_output = client.responses.create(
    model=model_name,
    tools=[code_interpreter_tool],
    input="Use code to print hello world.",
    include=["code_interpreter_call.outputs"],
)

# Indices depend on the order of items in output (e.g. text then code_interpreter_call)
print(response_with_output.output[1].outputs)
```

---

## 3. Custom Azure container (optional)

Use a custom container when you need per-chat or per-session isolation, or when you want to control lifecycle (e.g. `expires_after`). The client header must match the model used for code execution.

**Client:** Use `get_openai_client(additional_headers={"x-model": model_name})` and use the same `model` in `responses.create`.

**Create container:** Call `client.containers.create` with a name (include something like `chat_id` to separate chats) and `expires_after` (e.g. `{"anchor": "last_active_at", "minutes": 20}`).

**Tool:** Use `CodeInterpreter(type="code_interpreter", container=container.id)`.

```python
from openai.types.responses.tool_param import CodeInterpreter
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.language_model import LanguageModelName

model_name = LanguageModelName.AZURE_GPT_5_2025_0807
# Client header should match the model used for code execution
client = get_openai_client(additional_headers={"x-model": model_name})

container = client.containers.create(
    name="code_execution_container",
    expires_after={"anchor": "last_active_at", "minutes": 20},
)

code_interpreter_tool = CodeInterpreter(type="code_interpreter", container=container.id)

response = client.responses.create(
    model=model_name,
    tools=[code_interpreter_tool],
    input="Use code to print hello world.",
    include=["code_interpreter_call.outputs"],
)
```

---

## 4. Uploading and downloading files from containers

File upload and download apply to **custom containers** (you need a `container_id`). With auto containers, the API manages storage differently.

### Upload

Use `client.containers.files.create(container_id=container.id, file=(filename, file_content))` where `file_content` is for example **bytes** (other formats supported, check OpenAI documentation). The call returns a file object with `.id`; store it for later (e.g. to avoid re-uploading or to download).

```python
# Example: upload a small CSV as bytes
csv_content = b"name,value\na,1\nb,2\n"
openai_file = client.containers.files.create(
    container_id=container.id,
    file=("data.csv", csv_content),
)
file_id = openai_file.id  # store for later
```

### Download

- **Metadata:** `client.containers.files.retrieve(container_id=..., file_id=...)`
- **Content (bytes):** `client.containers.files.content.retrieve(container_id=..., file_id=...)`

Container lifecycle (e.g. `expires_after`) applies to these files as well.

### Checking if a file exists

Call `client.containers.files.retrieve(container_id=..., file_id=...)`. It raises `openai.NotFoundError` if the file does not exist. Use try/except to decide whether to upload or skip.

```python
from openai import NotFoundError

try:
    _ = client.containers.files.retrieve(container_id=container.id, file_id=file_id)
    # file exists, skip upload
except NotFoundError:
    # upload the file
    openai_file = client.containers.files.create(...)
```

### Checking if a container exists (and is usable)

Call `client.containers.retrieve(container_id)`. It raises `openai.NotFoundError` if the container does not exist. If it exists, check `container.status` — only treat as usable when `status in ["active", "running"]`; otherwise create a new container.

```python
from openai import NotFoundError

try:
    container = client.containers.retrieve(container_id)
    if container.status not in ["active", "running"]:
        # create a new container
        container = client.containers.create(...)
except NotFoundError:
    container = client.containers.create(...)
```

---

## Example scripts

- [code_execution_openai_client.py](../examples_from_docs/code_execution_openai_client.py) — quick start with auto container and including code outputs
- [code_execution_custom_azure_container.py](../examples_from_docs/code_execution_custom_azure_container.py) — custom container with `CodeInterpreter` and lifecycle control
