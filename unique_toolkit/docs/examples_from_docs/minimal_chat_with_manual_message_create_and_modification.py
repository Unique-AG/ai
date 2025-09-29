# %%
from unique_toolkit import (
    ChatService,
    ContentService,
)
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings

settings = UniqueSettings.from_env_auto_with_sdk_init()
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    # Initialize services from event
    chat_service = ChatService(event)
    content_service = ContentService.from_event(event)
    assistant_message = chat_service.create_assistant_message(
        content="Hello from Unique",
    )
    chat_service.modify_assistant_message(
        content="Modified User Message", message_id=assistant_message.id
    )
