# ~/~ begin <<docs/modules/examples/identity/identity_service.md#./docs/.python_files/identity_list_users_and_groups.py>>[init]
# ~/~ begin <<docs/modules/examples/identity/identity_service.md#identity_service_setup>>[init]
# ~/~ begin <<docs/setup/_common_imports.md#common_imports>>[init]
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent 
from unique_toolkit import ChatService, ContentService, EmbeddingService, LanguageModelService, LanguageModelName, KnowledgeBaseService
from unique_toolkit.experimental import Identity
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
from unique_toolkit.experimental import Identity
identity = Identity.from_settings()
# ~/~ end
# ~/~ begin <<docs/modules/examples/identity/identity_service.md#identity_list_users_and_groups>>[init]
users = identity.users.list(take=10)
for user in users:
    print(user.id, user.display_name, user.email)

groups = identity.groups.list(take=10)
for group in groups:
    print(group.id, group.name)
# ~/~ end
# ~/~ end
