# Code Execution — Unique Platform Patterns

This tutorial covers Unique-specific patterns for running code execution in a production assistant. It assumes familiarity with the basics covered in [Code Execution with the OpenAI SDK](./code_execution_openai_sdk.md).

## What You'll Learn

- Calling the Responses API through `ChatService` instead of the raw OpenAI client
- Working with the `ResponsesLanguageModelStreamResponse` output object and its convenience properties
- Persisting container and file state across stateless turns using `ShortTermMemoryService`

## Prerequisites

- `unique_toolkit` with a configured `ChatEvent` (or equivalent service init)
- A model that supports code execution (e.g. `LanguageModelName.AZURE_GPT_5_2025_0807`)
- A custom Azure container (required for file upload/download and state reuse — see [Code Execution with the OpenAI SDK](./code_execution_openai_sdk.md#3-custom-azure-container-optional))

---

## 1. Calling the Responses API via ChatService

Use `chat_service.complete_responses_with_references()` (sync) or `complete_responses_with_references_async()` (async) instead of calling `client.responses.create` directly. These methods handle authentication, streaming, and message writing to the chat automatically.

The signature accepts the same `tools`, `include`, and `messages` arguments as the raw API:

```python
from openai.types.responses.tool_param import CodeInterpreter
from unique_toolkit.language_model import LanguageModelName

code_interpreter_tool = CodeInterpreter(type="code_interpreter", container=container_id)

response = chat_service.complete_responses_with_references(
    model_name=LanguageModelName.AZURE_GPT_5_2025_0807,
    messages="Read data.csv and plot a histogram. Save the plot as histogram.png.",
    tools=[code_interpreter_tool],
    include=["code_interpreter_call.outputs"],
)
```

For the async variant:

```python
response = await chat_service.complete_responses_with_references_async(
    model_name=LanguageModelName.AZURE_GPT_5_2025_0807,
    messages="Read data.csv and plot a histogram. Save the plot as histogram.png.",
    tools=[code_interpreter_tool],
    include=["code_interpreter_call.outputs"],
)
```

---

## 2. The ResponsesLanguageModelStreamResponse output object

`complete_responses_with_references` returns a `ResponsesLanguageModelStreamResponse`. Its `.output` field is the raw `list[ResponseOutputItem]` — identical in structure to what you get from `client.responses.create`. In addition, the object exposes convenience properties that save you from iterating manually:

| Property | Type | Description |
|---|---|---|
| `.output` | `list[ResponseOutputItem]` | Raw output items (text, code calls, etc.) |
| `.container_files` | `list[AnnotationContainerFileCitation]` | All `container_file_citation` annotations across all output messages |
| `.code_interpreter_calls` | `list[ResponseCodeInterpreterToolCall]` | All code interpreter call items |

### Downloading model-generated files

Instead of manually walking `.output` to find annotations (as shown in the OpenAI SDK tutorial), use `.container_files` directly:

```python
from unique_toolkit.framework_utilities.openai.client import get_openai_client

client = get_openai_client()

for citation in response.container_files:
    file_content = client.containers.files.content.retrieve(
        citation.file_id,
        container_id=citation.container_id,
    )
    print(f"{citation.filename}: {len(file_content.read())} bytes")
```

Each `citation` has `.file_id`, `.filename`, and `.container_id`.

---

## 3. Persisting state with ShortTermMemoryService

The assistant is stateless — a new handler instance is created for every incoming message. Without persistence, a new container would be created on every turn and previously uploaded files would be lost. Use `PersistentShortMemoryManager` to save the `container_id` and uploaded file IDs to chat-scoped short-term memory, so they can be reused on the next turn.

### Define a memory schema

```python
from pydantic import BaseModel

class CodeExecutionMemory(BaseModel):
    container_id: str | None = None
    file_ids: dict[str, str] = {}  # Unique file id -> OpenAI container file id
```

### Set up the manager

Instantiate at chat scope (using `chat_id`, not `message_id`) so memory persists across turns:

```python
from unique_toolkit.short_term_memory.service import ShortTermMemoryService
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)

stm_service = ShortTermMemoryService(
    company_id=event.company_id,
    user_id=event.user_id,
    chat_id=event.payload.chat_id,
    message_id=None,  # chat-level scope, not message-level
)
memory_manager = PersistentShortMemoryManager(
    short_term_memory_service=stm_service,
    short_term_memory_schema=CodeExecutionMemory,
    short_term_memory_name="code_execution", # Ideally include a chat_id in the name
)
```

### Per-turn pattern

Load at the start of each turn, update in place, save at the end:

```python
from openai import NotFoundError

# 1. Load (returns None if no memory saved yet)
memory = await memory_manager.load_async() or CodeExecutionMemory()

# 2. Create or reuse container
if memory.container_id is not None:
    try:
        container = await client.containers.retrieve(memory.container_id)
        # This field is not well-typed in the openai sdk, this was found through trial and error
        if container.status not in ["active", "running"]: 
            memory = CodeExecutionMemory()  # reset: stale container
    except NotFoundError:
        memory = CodeExecutionMemory()  # reset: container gone

if memory.container_id is None:
    container = await client.containers.create(
        name=f"code_execution_{event.payload.chat_id}",
        expires_after={"anchor": "last_active_at", "minutes": 20},
    )
    memory.container_id = container.id

# 3. Upload files (skip if already uploaded)
for file in files_to_upload:
    if file.id in memory.file_ids:
        try:
            await client.containers.files.retrieve(
                memory.file_ids[file.id], container_id=memory.container_id
            )
            continue  # already there
        except NotFoundError:
            pass  # fall through to re-upload

    openai_file = await client.containers.files.create(
        memory.container_id,
        file=(file.name, file.content_bytes),
    )
    memory.file_ids[file.id] = openai_file.id

# 4. Run inference
code_interpreter_tool = CodeInterpreter(
    type="code_interpreter", container=memory.container_id
)
response = await chat_service.complete_responses_with_references_async(
    model_name=LanguageModelName.AZURE_GPT_5_2025_0807,
    messages=user_message,
    tools=[code_interpreter_tool],
    include=["code_interpreter_call.outputs"],
)

# 5. Save updated memory
await memory_manager.save_async(memory)
```

---

## Example script

- [code_execution_unique_platform.py](../examples_from_docs/code_execution_unique_platform.py) — full end-to-end example combining all three patterns above
