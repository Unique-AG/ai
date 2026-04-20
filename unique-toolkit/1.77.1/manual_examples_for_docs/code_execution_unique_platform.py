# %%
# Code execution — Unique platform patterns
# Covers: ChatService responses API, ResponsesLanguageModelStreamResponse, ShortTermMemory

from openai import NotFoundError
from openai.types.responses.tool_param import CodeInterpreter
from pydantic import BaseModel

from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.chat.service import Content
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.language_model import LanguageModelName
from unique_toolkit.short_term_memory.service import ShortTermMemoryService
from unique_toolkit import ChatService
from unique_toolkit.services.knowledge_base import KnowledgeBaseService

settings = UniqueSettings.from_env_auto_with_sdk_init("qa.env")

# %%
# Memory schema — persists container_id and uploaded file_ids across turns

class CodeExecutionMemory(BaseModel):
    container_id: str | None = None
    file_ids: dict[str, str] = {}  # internal_file_id -> OpenAI container file id


# %%
# Per-turn handler

model_name = LanguageModelName.AZURE_GPT_5_2025_0807

for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    chat_service = ChatService(event)
    kb_service = KnowledgeBaseService.from_event(event)
    client = get_openai_client(
        additional_headers={"x-model": model_name}
    )

    # %%
    # Set up short-term memory manager at chat scope (message_id=None)

    stm_service = ShortTermMemoryService(
        company_id=event.company_id,
        user_id=event.user_id,
        chat_id=event.payload.chat_id,
        message_id=None,
    )
    memory_manager: PersistentShortMemoryManager[CodeExecutionMemory] = (
        PersistentShortMemoryManager(
            short_term_memory_service=stm_service,
            short_term_memory_schema=CodeExecutionMemory,
            short_term_memory_name=f"code_execution_{event.payload.chat_id}", 
        )
    )

    # %%
    # Load memory from previous turn (None if first turn)

    memory = memory_manager.load_sync() or CodeExecutionMemory()
    print(f"Loaded memory: container_id={memory.container_id}, files={list(memory.file_ids)}")

    # %%
    # Create or reuse the container

    if memory.container_id is not None:
        try:
            container = client.containers.retrieve(memory.container_id)
            # This field is not well-typed in the openai sdk, this was found through trial and error
            if container.status not in ["active", "running"]:
                print(f"Container status is '{container.status}', recreating")
                memory = CodeExecutionMemory()
        except NotFoundError:
            print("Container not found, recreating")
            memory = CodeExecutionMemory()

    if memory.container_id is None:
        container = client.containers.create(
            name=f"code_execution_{event.payload.chat_id}",
            expires_after={"anchor": "last_active_at", "minutes": 20},
        )
        memory.container_id = container.id
        print(f"Created container: {memory.container_id}")
    else:
        print(f"Reusing container: {memory.container_id}")

    # %%
    # Upload files to the container, skipping any already present
    # Replace `files_to_upload` with actual file objects that have .id, .name, .content_bytes

    files_to_upload: list[Content] = []  # e.g. fetched from KnowledgeBaseService

    for file in files_to_upload:
        if file.id in memory.file_ids:
            try:
                client.containers.files.retrieve(
                    memory.file_ids[file.id],
                    container_id=memory.container_id,
                )
                print(f"File {file.id} already in container, skipping")
                continue
            except NotFoundError:
                pass  # file disappeared — re-upload below

        file_content = kb_service.download_content_to_bytes(
            content_id=file.id
        )
        openai_file = client.containers.files.create(
            memory.container_id,
            file=(file.key, file_content),
        )
        memory.file_ids[file.id] = openai_file.id
        print(f"Uploaded {file.key} -> {openai_file.id}")

    # %%
    # Call the Responses API via ChatService
    # complete_responses_with_references handles auth, streaming, and message writing

    code_interpreter_tool = CodeInterpreter(
        type="code_interpreter",
        container=memory.container_id,
    )

    response = chat_service.complete_responses_with_references(
        model_name=model_name,
        messages=event.payload.user_message.text,
        tools=[code_interpreter_tool],
        include=["code_interpreter_call.outputs"],
    )

    # %%
    # Inspect code interpreter calls from the response
    # response.code_interpreter_calls is a convenience property on ResponsesLanguageModelStreamResponse

    for call in response.code_interpreter_calls:
        print(f"Code interpreter call: {call.id}")

    # %%
    # Download files generated by the model during code execution
    # response.container_files parses all container_file_citation annotations automatically

    for citation in response.container_files:
        file_content = client.containers.files.content.retrieve(
            citation.file_id,
            container_id=citation.container_id,
        )
        generated_bytes = file_content.read()
        print(f"Generated file: {citation.filename}  ({len(generated_bytes)} bytes)")

    # %%
    # Save updated memory (new container_id and/or file_ids) for next turn

    memory_manager.save_sync(memory)
    print(f"Saved memory: container_id={memory.container_id}, files={list(memory.file_ids)}")
