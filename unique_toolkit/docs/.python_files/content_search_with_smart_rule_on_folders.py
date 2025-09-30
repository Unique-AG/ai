# ~/~ begin <<docs/modules/examples/content/content_service.md#./docs/.python_files/content_search_with_smart_rule_on_folders.py>>[init]
# ~/~ begin <<docs/modules/examples/content/content_service.md#smart_rules_imports>>[init]
from unique_toolkit.smart_rules.compile import Statement, Operator, AndStatement, OrStatement
# ~/~ end
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
# ~/~ begin <<docs/modules/examples/content/content_service.md#smart_rule_folder_content>>[init]
smart_rule_folder_content = Statement(operator=Operator.EQUALS, 
                                      value=f"{scope_id}", 
                                      path=["folderIdPath"])

metadata_filter = smart_rule_folder_content.model_dump(mode="json")
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_combined_with_metadafilter>>[init]


content_chunks = content_service.search_content_chunks(
    search_string="Harry Potter",
    search_type=ContentSearchType.COMBINED,
    limit=15,
    metadata_filter=metadata_filter
)
# ~/~ end
# ~/~ end
