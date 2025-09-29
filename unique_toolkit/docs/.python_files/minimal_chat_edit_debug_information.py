# ~/~ begin <<docs/modules/examples/chat/chat_service.md#docs/.python_files/minimal_chat_edit_debug_information.py>>[init]
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
from unique_toolkit.content.schemas import ContentSearchType, ContentRerankerConfig, ContentChunk, ContentReference
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
    # ~/~ begin <<docs/modules/examples/chat/chat_service.md#chat_service_create_assistant_message>>[init]
    assistant_message = chat_service.create_assistant_message(
            content="Hello from Unique",
        )
    # ~/~ end
    # ~/~ begin <<docs/modules/examples/chat/chat_service.md#chat_service_modify_assistant_message>>[init]
    chat_service.modify_assistant_message(
            content="Modified User Message",
            message_id=assistant_message.id
        )
    # ~/~ end
    # ~/~ begin <<docs/modules/examples/chat/chat_service.md#chat_service_modify_user_message_debug_info>>[init]

    debug_info = event.get_initial_debug_info()
    debug_info.update({"timing": "20s till completion"})


    chat_service.modify_user_message(
            content="Modified User Message",
            message_id=event.payload.user_message.id,
            debug_info=debug_info
        )
    # ~/~ end
    # ~/~ begin <<docs/modules/examples/chat/chat_service.md#chat_service_free_user_input>>[init]
    chat_service.free_user_input()
    # ~/~ end
# ~/~ end
