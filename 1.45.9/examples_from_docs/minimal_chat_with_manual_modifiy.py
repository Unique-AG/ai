# %%
import time

from unique_toolkit import (
    ChatService,
    KnowledgeBaseService,
)
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings

settings = UniqueSettings.from_env_auto_with_sdk_init()
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    # Initialize services from event
    chat_service = ChatService(event)
    kb_service = KnowledgeBaseService.from_event(event)
    chat_service.modify_assistant_message(
        content="Intermediate assistant message",
    )
    time.sleep(2)
    chat_service.modify_assistant_message(
        content="Final assistant message",
    )
