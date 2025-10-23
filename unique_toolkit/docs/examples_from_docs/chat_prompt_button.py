# %%
from unique_toolkit import (
    ChatService,
    KnowledgeBaseService,
)
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.chat.rendering import create_prompt_button_string

settings = UniqueSettings.from_env_auto_with_sdk_init()
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    # Initialize services from event
    chat_service = ChatService(event)
    kb_service = KnowledgeBaseService.from_event(event)
    prompt_button_string = create_prompt_button_string(
        button_text="Click me", next_user_message="Next user message"
    )
    chat_service.create_assistant_message(
        content=f"Here is a prompt button:\n {prompt_button_string}",
    )
