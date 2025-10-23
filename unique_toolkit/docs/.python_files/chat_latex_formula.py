# ~/~ begin <<docs/modules/examples/chat/avanced_rendering.md#docs/.python_files/chat_latex_formula.py>>[init]
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
from unique_toolkit.chat.rendering import create_prompt_button_string, create_latex_formula_string
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
    # ~/~ begin <<docs/modules/examples/chat/avanced_rendering.md#rendering_latex_formula>>[init]
    latex_formula_string = create_latex_formula_string(
        latex_expression=r"\int_{a}^{b} f(x) \, dx"
    )
    chat_service.create_assistant_message(
        content=f"Here is a latex formula: {latex_formula_string}",
    )
    # ~/~ end
    # ~/~ begin <<docs/tutorials/file_creation_and_upload_to_chat.md#free_user_input>>[init]
    chat_service.free_user_input()
    # ~/~ end
# ~/~ end
