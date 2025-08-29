# ~/~ begin <<docs/modules/examples/chat/chat_service.md#docs/.python_files/minimal_chat_with_manual_message_create_free_user_input.py>>[init]
# ~/~ begin <<docs/application_types/event_driven_applications.md#full_sse_setup>>[init]
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
    # ~/~ begin <<docs/modules/examples/chat/chat_service.md#chat_service_modify_assistant_message>>[init]
    chat_service.modify_assistant_message(
            content="Modified User Message",
            message_id=assistant_message.id
        )
    # ~/~ end
    # ~/~ begin <<docs/modules/examples/chat/chat_service.md#chat_service_free_user_input>>[init]
    chat_service.free_user_input()
    # ~/~ end
# ~/~ end
