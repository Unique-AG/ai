# %%
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
)

settings = UniqueSettings.from_env_auto_with_sdk_init()
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    # Initialize services from event
    chat_service = ChatService(event)
    kb_service = KnowledgeBaseService.from_event(event)
    messages = (
        OpenAIMessageBuilder()
        .system_message_append(content="You are a helpful assistant")
        .user_message_append(content=event.payload.user_message.text)
        .messages
    )

    try:
        old_memory = chat_service.find_chat_memory(key="user_message")
        print(old_memory.value)
    except Exception:
        print("No chat memory found with key 'user_message'")

    chat_service.create_chat_memory(
        key="user_message", value={"test_memory": "test_value"}
    )

    chat_service.complete_with_references(
        messages=messages, model_name=LanguageModelName.AZURE_GPT_4o_2024_1120
    )
