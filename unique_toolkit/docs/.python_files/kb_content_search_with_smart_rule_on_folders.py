# ~/~ begin <<docs/modules/examples/content/smart_rules.md#./docs/.python_files/kb_content_search_with_smart_rule_on_folders.py>>[init]
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
# ~/~ begin <<docs/modules/examples/content/smart_rules.md#smart_rule_custom_metadata>>[init]
smart_rule_custom = Statement(operator=Operator.EQUALS, 
                                      value=f"customValue", 
                                      path=["customMetaData"])

metadata_filter = smart_rule_custom.model_dump(mode="json")
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/smart_rules.md#kb_content_search>>[init]
infos =kb_service.get_paginated_content_infos(
    metadata_filter=metadata_filter
)
# ~/~ end
# ~/~ end
