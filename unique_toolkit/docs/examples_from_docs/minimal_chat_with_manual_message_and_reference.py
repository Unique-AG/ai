# %%
from unique_toolkit import (
    ChatService,
)
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import (
    ContentReference,
)

settings = UniqueSettings.from_env_auto_with_sdk_init()
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    chat_service = ChatService(event)
    assistant_message = chat_service.create_assistant_message(
        content="Hello from Unique",
    )
    chat_service.modify_assistant_message(
        content="Modified User Message", message_id=assistant_message.id
    )
    chat_service.create_assistant_message(
        content="Hello from Unique <sup>0</sup>",
        references=[
            ContentReference(
                source="source0",
                url="https://www.unique.ai",
                name="reference_name",
                sequence_number=0,
                source_id="source_id_0",
                id="id_0",
            )
        ],
    )
