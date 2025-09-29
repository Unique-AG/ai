# ~/~ begin <<docs/modules/examples/chat/chat_service.md#docs/.python_files/minimal_chat_app.py>>[init]
# ~/~ begin <<docs/application_types/event_driven_applications.md#full_sse_setup>>[init]
# ~/~ begin <<docs/setup/_common_imports.md#common_imports>>[init]
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent 
from unique_toolkit import ChatService, ContentService, EmbeddingService, LanguageModelService, LanguageModelName
from unique_toolkit.chat.schemas import ChatMessageAssessmentStatus, ChatMessageAssessmentType, ChatMessageAssessmentLabel
import os
import io
import tempfile
import requests
from pathlib import Path
from unique_toolkit.content.schemas import ContentSearchType, ContentRerankerConfig, ContentChunk
import unique_sdk
from pydantic import BaseModel, Field
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
from pydantic import Field
from unique_toolkit import LanguageModelToolDescription
# ~/~ end
# ~/~ begin <<docs/application_types/event_driven_applications.md#unique_setup_settings_sdk_from_env>>[init]
settings = UniqueSettings.from_env_auto_with_sdk_init()
# ~/~ end
# ~/~ begin <<docs/application_types/event_driven_applications.md#obtaining_sse_client_with_chat_event>>[init]
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    chat_service = ChatService(event)
# ~/~ end
# ~/~ end
    # ~/~ begin <<docs/modules/examples/chat/chat_service.md#trivial_message_from_user>>[init]
    messages = (
            OpenAIMessageBuilder()
            .system_message_append(content="You are a helpful assistant")
            .user_message_append(content=event.payload.user_message.text)
            .messages
        )
    # ~/~ end
    # ~/~ begin <<docs/modules/examples/chat/chat_service.md#chat_service_complete_with_references>>[init]
    chat_service.complete_with_references(
            messages = messages,
            model_name = LanguageModelName.AZURE_GPT_4o_2024_1120)
    # ~/~ end
# ~/~ end