# %%
import mimetypes

from unique_toolkit import (
    ChatService,
    KnowledgeBaseService,
    LanguageModelName,
)
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
    OpenAIUserMessageBuilder,
)

settings = UniqueSettings.from_env_auto_with_sdk_init()
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    # Initialize services from event
    chat_service = ChatService(event)
    kb_service = KnowledgeBaseService.from_event(event)
    images, documents = chat_service.download_chat_images_and_documents()

    if len(documents) > 0:
        doc_bytes = chat_service.download_chat_content_to_bytes(
            content_id=documents[0].id
        )
    img_bytes = None
    img_mime_type = None
    if len(images) > 0:
        img_bytes = chat_service.download_chat_content_to_bytes(content_id=images[0].id)
        img_mime_type, _ = mimetypes.guess_type(images[0].key)

    builder = OpenAIMessageBuilder().system_message_append(
        content="You are a helpful assistant."
    )

    if img_bytes is not None and img_mime_type is not None:
        builder.user_message_append(
            content=OpenAIUserMessageBuilder()
            .append_text("What is the content of the image?")
            .append_image(content=img_bytes, mime_type=img_mime_type)
            .iterable_content
        )
    else:
        builder.user_message_append(content="Can you see the image? If not, say so.")
    chat_service.complete_with_references(
        messages=builder.messages, model_name=LanguageModelName.AZURE_GPT_4o_2024_1120
    )

    chat_service.free_user_input()
