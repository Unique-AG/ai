# ~/~ begin <<docs/modules/examples/chat/chat_service.md#docs/.python_files/minimal_chat_with_message_assessment.py>>[init]
# ~/~ begin <<docs/modules/examples/chat/chat_service.md#message_assessment_imports>>[init]
from unique_toolkit.chat.schemas import ChatMessageAssessmentStatus, ChatMessageAssessmentType, ChatMessageAssessmentLabel
# ~/~ end
# ~/~ begin <<docs/modules/examples/chat/chat_service.md#full_sse_setup>>[init]
# ~/~ begin <<docs/plattforms/openai/openai.md#common_library_imports>>[init]
from pathlib import Path
from pydantic import BaseModel
# ~/~ end
# ~/~ begin <<docs/plattforms/openai/openai.md#openai_toolkit_imports>>[init]
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
# ~/~ end
# ~/~ begin <<docs/application_types/event_driven_applications.md#unique_settings_import>>[init]
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.app.init_sdk import init_unique_sdk
# ~/~ end
# ~/~ begin <<docs/application_types/event_driven_applications.md#unique_sse_setup_import>>[init]
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent 
# ~/~ end
# ~/~ begin <<docs/modules/examples/chat/chat_service.md#unique_chat_service_import>>[init]
from unique_toolkit import ChatService
# ~/~ end
# ~/~ begin <<docs/application_types/event_driven_applications.md#unique_setup_settings_sdk_from_env>>[init]
settings = UniqueSettings.from_env_auto_with_sdk_init()
# ~/~ end
# ~/~ begin <<docs/modules/examples/chat/chat_service.md#default_language_model>>[init]
from unique_toolkit import LanguageModelName

model_name = LanguageModelName.AZURE_GPT_4o_2024_1120
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
    # ~/~ begin <<docs/modules/examples/chat/chat_service.md#chat_service_create_message_assessment>>[init]
    if not assistant_message.id:
        raise ValueError("Assistant message ID is not set")

    message_assessment = chat_service.create_message_assessment(
            assistant_message_id=assistant_message.id,
            status=ChatMessageAssessmentStatus.PENDING,
            type=ChatMessageAssessmentType.COMPLIANCE,
            title="Following Guidelines",
            explanation="",
            is_visible=True,
        )
    # ~/~ end
    # ~/~ begin <<docs/modules/examples/chat/chat_service.md#chat_service_modify_message_assessment>>[init]
    chat_service.modify_message_assessment(
        assistant_message_id=assistant_message.id,
        status=ChatMessageAssessmentStatus.DONE,
        type=ChatMessageAssessmentType.COMPLIANCE,
        title="Following Guidelines",
        explanation="The agents choice of words is according to our guidelines.",
        label=ChatMessageAssessmentLabel.GREEN,
    )
    # ~/~ end
# ~/~ end
