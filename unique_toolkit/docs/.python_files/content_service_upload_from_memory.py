# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_upload_from_memory>>[init]
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_setup>>[init]
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
from unique_toolkit.content.schemas import ContentSearchType, ContentRerankerConfig
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
# ~/~ begin <<docs/modules/examples/content/content_service.md#initialize_content_service_standalone>>[init]
content_service = ContentService.from_settings_filename()
# ~/~ end
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#load_demo_variables>>[init]
from dotenv import dotenv_values
demo_env_vars = dotenv_values(Path(__file__).parent/"demo.env")
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#env_scope_id>>[init]
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_upload_bytes>>[init]
content_bytes = b"Your file content here"
content = content_service.upload_content_from_bytes(
    content=content_bytes,
    content_name="document.txt",
    mime_type="text/plain",
    scope_id=scope_id,
    metadata={"category": "documentation", "version": "1.0"}
)
# ~/~ end
# ~/~ end
