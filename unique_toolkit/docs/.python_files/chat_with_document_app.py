# ~/~ begin <<docs/modules/examples/chat/chat_document_handling.md#docs/.python_files/chat_with_document_app.py>>[init]
# ~/~ begin <<docs/application_types/event_driven_applications.md#full_sse_setup_with_services>>[init]
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
    # ~/~ begin <<docs/application_types/event_driven_applications.md#init_services_from_event>>[init]
    # Initialize services from event
    chat_service = ChatService(event)
    kb_service= KnowledgeBaseService.from_event(event)
    # ~/~ end
# ~/~ end
    # ~/~ begin <<docs/modules/examples/chat/chat_document_handling.md#chat_service_document_and_image_download>>[init]
    images, documents = chat_service.download_chat_images_and_documents()

    if len(documents) > 0:
        doc_bytes = chat_service.download_chat_content_to_bytes(content_id=documents[0].id)
    # ~/~ end
    # ~/~ begin <<docs/modules/examples/chat/chat_document_handling.md#chat_service_images_message_building>>[init]
    img_bytes = None
    img_mime_type = None
    if len(images) > 0:
        img_bytes = chat_service.download_chat_content_to_bytes(content_id=images[0].id)
        img_mime_type, _ = mimetypes.guess_type(images[0].key)

    builder = (OpenAIMessageBuilder()
            .system_message_append(content="You are a helpful assistant."))

    if img_bytes is not None and img_mime_type is not None:
        builder.user_message_append(
                content=OpenAIUserMessageBuilder()
                .append_text("What is the content of the image?")
                .append_image(content=img_bytes, mime_type=img_mime_type)
                .iterable_content
            )
    else:
        builder.user_message_append(content="Can you see the image? If not, say so.")
    # ~/~ end
    # ~/~ begin <<docs/modules/examples/chat/chat_document_handling.md#chat_service_send_message>>[init]
    chat_service.complete_with_references(
        messages=builder.messages,
        model_name=LanguageModelName.AZURE_GPT_4o_2024_1120
    )

    chat_service.free_user_input()
    # ~/~ end
# ~/~ end
