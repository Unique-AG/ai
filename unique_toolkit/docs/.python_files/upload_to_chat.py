# ~/~ begin <<docs/tutorials/file_creation_and_upload_to_chat.md#docs/.python_files/upload_to_chat.py>>[init]
# ~/~ begin <<docs/application_types/event_driven_applications.md#full_sse_setup>>[init]
# ~/~ begin <<docs/setup/_common_imports.md#common_imports>>[init]
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent 
from unique_toolkit import ChatService, ContentService, EmbeddingService, LanguageModelService, LanguageModelName, KnowledgeBaseService
from unique_toolkit.chat.schemas import ChatMessageAssessmentStatus, ChatMessageAssessmentType, ChatMessageAssessmentLabel
import os
import io
import tempfile
import requests
import mimetypes
from pathlib import Path
from unique_toolkit.content.schemas import ContentSearchType, ContentRerankerConfig, ContentChunk, ContentReference
import unique_sdk
from pydantic import BaseModel, Field
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
    OpenAIUserMessageBuilder
)
from pydantic import Field
from unique_toolkit import LanguageModelToolDescription
# ~/~ end
# ~/~ begin <<docs/application_types/event_driven_applications.md#unique_setup_settings_sdk_from_env>>[init]
settings = UniqueSettings.from_env_auto_with_sdk_init()
# ~/~ end
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
# ~/~ end
    settings.update_from_event(event)
    # ~/~ begin <<docs/application_types/event_driven_applications.md#init_services_from_event>>[init]
    # Initialize services from event
    chat_service = ChatService(event)
    content_service = ContentService.from_event(event)
    # ~/~ end
    # ~/~ begin <<docs/tutorials/file_creation_and_upload_to_chat.md#upload_with_reference_initial_message>>[init]

    assistant_message =chat_service.create_assistant_message(
        content="Hi there, the agent has started to create your document.",
    )
    # ~/~ end
    # ~/~ begin <<docs/tutorials/file_creation_and_upload_to_chat.md#upload_with_reference_document_creation>>[init]
    content_bytes = b"Hello, world!"
    # ~/~ end
    # ~/~ begin <<docs/tutorials/file_creation_and_upload_to_chat.md#upload_with_reference_upload_document>>[init]
    uploaded_content = content_service.upload_content_from_bytes(
            content=content_bytes,
            content_name="document.txt",
            mime_type="text/plain",
            chat_id=event.payload.chat_id,
            skip_ingestion=True,
        )
    # ~/~ end
    # ~/~ begin <<docs/tutorials/file_creation_and_upload_to_chat.md#upload_with_reference_referencing_in_message>>[init]
    reference = ContentReference(
            id=uploaded_content.id,
            sequence_number=1,
            message_id=event.payload.assistant_message.id,
            name="document.txt",
            source=event.payload.name,
            source_id=event.payload.chat_id,
            url=f"unique://content/{uploaded_content.id}",
        )


    chat_service.modify_assistant_message(
                    content="Please find the translated document below in the references.",
                    message_id=assistant_message.id, 
                    references=[reference],
                )
    # ~/~ end
    # ~/~ begin <<docs/tutorials/file_creation_and_upload_to_chat.md#free_user_input>>[init]
    chat_service.free_user_input()
    # ~/~ end
# ~/~ end
