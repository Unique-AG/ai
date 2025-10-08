# %%
from unique_toolkit import (
    ChatService,
    KnowledgeBaseService,
)
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import (
    ContentReference,
)

settings = UniqueSettings.from_env_auto_with_sdk_init()
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    settings.update_from_event(event)
    # Initialize services from event
    chat_service = ChatService(event)
    kb_service = KnowledgeBaseService.from_event(event)

    assistant_message = chat_service.create_assistant_message(
        content="Hi there, the agent has started to create your document.",
    )
    content_bytes = b"Hello, world!"
    uploaded_content = kb_service.upload_content_from_bytes(
        content=content_bytes,
        content_name="document.txt",
        mime_type="text/plain",
        chat_id=event.payload.chat_id,
        skip_ingestion=True,
    )
    reference = ContentReference(
        id=uploaded_content.id,
        sequence_number=1,
        message_id=event.payload.assistant_message.id,
        name="document.txt",
        source=event.payload.name,
        source_id=event.payload.chat_id,
        url=f"unique://content/{uploaded_content.id}",
    )

    chat_service.modify_assistant_message(
        content="Please find the translated document below in the references.",
        message_id=assistant_message.id,
        references=[reference],
    )
    chat_service.free_user_input()
