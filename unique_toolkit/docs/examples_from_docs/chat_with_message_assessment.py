# %%
from unique_toolkit import (
    ChatService,
    KnowledgeBaseService,
)
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.chat.schemas import (
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
)

settings = UniqueSettings.from_env_auto_with_sdk_init()
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    # Initialize services from event
    chat_service = ChatService(event)
    kb_service = KnowledgeBaseService.from_event(event)
    assistant_message = chat_service.create_assistant_message(
        content="Hello from Unique",
    )
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
    chat_service.modify_message_assessment(
        assistant_message_id=assistant_message.id,
        status=ChatMessageAssessmentStatus.DONE,
        type=ChatMessageAssessmentType.COMPLIANCE,
        title="Following Guidelines",
        explanation="The agents choice of words is according to our guidelines.",
        label=ChatMessageAssessmentLabel.GREEN,
    )
