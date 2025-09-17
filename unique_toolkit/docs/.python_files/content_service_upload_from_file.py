# ~/~ begin <<docs/modules/examples/content/content_service.md#./docs/.python_files/content_service_upload_from_file.py>>[init]
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
content_service = ContentService.from_settings()
# ~/~ end
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#load_demo_variables>>[init]
from dotenv import dotenv_values
demo_env_vars = dotenv_values(Path(__file__).parent/"demo.env")
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#env_scope_id>>[init]
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
# ~/~ end
file_path = Path(__file__).parent/"test.txt"
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_upload_from_file>>[init]
# Configure ingestion settings
content = content_service.upload_content(
    path_to_content=str(file_path),
    content_name=Path(file_path).name,
    mime_type="text/plain",
    scope_id=scope_id,
    skip_ingestion=False, # Process the content for search
    metadata={"department": "legal", "classification": "confidential"}
)
# ~/~ end
# ~/~ end
