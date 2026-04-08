# ~/~ begin <<docs/modules/examples/elicitation/elicitation_service.md#docs/.python_files/elicitation_basic.py>>[init]
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
# ~/~ begin <<docs/modules/examples/elicitation/elicitation_service.md#elicitation_imports>>[init]
from unique_toolkit.elicitation import (
    ElicitationMode,
    ElicitationStatus,
    ElicitationDeclinedException,
    ElicitationCancelledException,
    ElicitationExpiredException,
)
# ~/~ end
# ~/~ begin <<docs/modules/examples/elicitation/elicitation_service.md#elicitation_helper_function>>[init]
def handle_elicitation_result(result):
    """Process elicitation result and raise appropriate exceptions for non-success."""
    if result.status == ElicitationStatus.ACCEPTED:
        return result.response_content
    elif result.status == ElicitationStatus.PENDING:
        return None
    elif result.status == ElicitationStatus.DECLINED:
        raise ElicitationDeclinedException()
    elif result.status == ElicitationStatus.CANCELLED:
        raise ElicitationCancelledException()
    elif result.status == ElicitationStatus.EXPIRED:
        raise ElicitationExpiredException()
# ~/~ end
# ~/~ begin <<docs/application_types/event_driven/index.md#full_sse_setup_with_services>>[init]
# ~/~ begin <<docs/application_types/event_driven/index.md#full_sse_setup>>[init]
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
# ~/~ begin <<docs/application_types/event_driven/event_driven_with_sse.md#unique_setup_settings_sdk_from_env>>[init]
settings = UniqueSettings.from_env_auto_with_sdk_init()
# ~/~ end
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
# ~/~ end
    # ~/~ begin <<docs/application_types/event_driven/index.md#init_services_from_event>>[init]
    # Initialize services from event
    chat_service = ChatService(event)
    kb_service= KnowledgeBaseService.from_event(event)
    # ~/~ end
# ~/~ end
    # ~/~ begin <<docs/modules/examples/elicitation/elicitation_service.md#elicitation_create_form>>[init]
    elicitation = chat_service.elicitation.create(
        mode=ElicitationMode.FORM,
        message="Please provide the required information",
        tool_name="data_collection",
        json_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Your Name"},
                "confirm": {"type": "boolean", "title": "I confirm"}
            },
            "required": ["name", "confirm"]
        }
    )
    # ~/~ end
    # ~/~ begin <<docs/modules/examples/elicitation/elicitation_service.md#elicitation_check_status>>[init]
    result = chat_service.elicitation.get(elicitation.id)
    
    if result.status == ElicitationStatus.PENDING:
        chat_service.modify_assistant_message(
            content="Waiting for your response..."
        )
    elif result.status == ElicitationStatus.ACCEPTED:
        user_data = result.response_content
        chat_service.modify_assistant_message(
            content=f"Thank you {user_data.get('name')}!"
        )
    elif result.status == ElicitationStatus.DECLINED:
        chat_service.modify_assistant_message(
            content="No problem, let me know if you change your mind."
        )
    elif result.status == ElicitationStatus.CANCELLED:
        chat_service.modify_assistant_message(
            content="Request was cancelled."
        )
    elif result.status == ElicitationStatus.EXPIRED:
        chat_service.modify_assistant_message(
            content="The request has expired. Please try again."
        )
    # ~/~ end
# ~/~ end
