# ~/~ begin <<docs/modules/examples/content/smart_rules.md#./docs/.python_files/remove_metadata_with_smart_rule.py>>[init]
# ~/~ begin <<docs/modules/examples/content/smart_rules.md#smart_rules_imports>>[init]
from unique_toolkit.smart_rules.compile import Statement, Operator, AndStatement, OrStatement
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/kb_service.md#kb_service_setup>>[init]
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
# ~/~ begin <<docs/modules/examples/content/kb_service.md#initialize_kb_service_standalone>>[init]
kb_service = KnowledgeBaseService.from_settings()
# ~/~ end
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/kb_service.md#load_demo_variables>>[init]
from dotenv import dotenv_values
demo_env_vars = dotenv_values(Path(__file__).parent/"demo.env")
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/kb_service.md#env_scope_id>>[init]
scope_id = demo_env_vars.get("UNIQUE_SCOPE_ID") or "unknown"
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/smart_rules.md#smart_rule_folder_content>>[init]
smart_rule_folder_content = Statement(operator=Operator.EQUALS, 
                                      value=f"{scope_id}", 
                                      path=["folderId"])

metadata_filter = smart_rule_folder_content.model_dump(mode="json")
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/smart_rules.md#kb_service_remove_metadata>>[init]
# Remove specific metadata keys from all matching files
updated_contents = kb_service.remove_contents_metadata(
    keys_to_remove=["department"],
    metadata_filter=metadata_filter
)

print(f"Removed metadata from {len(updated_contents)} files")
# ~/~ end
# ~/~ end
