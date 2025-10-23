# ~/~ begin <<docs/modules/examples/content/smart_rules.md#./docs/.python_files/kb_deletion_with_smart_rule_on_folders.py>>[init]
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
from unique_toolkit.chat.rendering import create_prompt_button_string, create_latex_formula_string
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
# ~/~ begin <<docs/modules/examples/content/smart_rules.md#upload_with_custom_metadata>>[init]
content_bytes = b"Your file content here"
content = kb_service.upload_content_from_bytes(
    content=content_bytes,
    content_name="document_custom.txt",
    mime_type="text/plain",
    scope_id=scope_id,
    metadata={"customMetaData": "customValue", "version": "1.0"}
)
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/kb_service.md#kb_service_upload_bytes>>[init]
content_bytes = b"Your file content here"
content = kb_service.upload_content_from_bytes(
    content=content_bytes,
    content_name="document.txt",
    mime_type="text/plain",
    scope_id=scope_id,
    metadata={"category": "documentation", "version": "1.0"}
)
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/smart_rules.md#smart_rule_custom_metadata>>[init]
smart_rule_custom = Statement(operator=Operator.EQUALS, 
                                      value=f"customValue", 
                                      path=["customMetaData"])

metadata_filter = smart_rule_custom.model_dump(mode="json")
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/smart_rules.md#smart_rule_folder_content>>[init]
smart_rule_folder_content = Statement(operator=Operator.EQUALS, 
                                      value=f"{scope_id}", 
                                      path=["folderId"])

metadata_filter = smart_rule_folder_content.model_dump(mode="json")
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/smart_rules.md#combined_folder_and_custom_metadata>>[init]
smart_rule_folders_and_mime = AndStatement(and_list=[smart_rule_folder_content, 
                                                     smart_rule_custom])
metadata_filter = smart_rule_folders_and_mime.model_dump(mode="json") 
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/smart_rules.md#kb_service_delete>>[init]
kb_service.delete_contents(
    metadata_filter=metadata_filter
)
# ~/~ end
# ~/~ end
