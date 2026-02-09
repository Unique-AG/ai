# %%
from unique_toolkit import (
    ChatService,
    KnowledgeBaseService,
)
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.chat.rendering import (
    create_latex_formula_string,
)

settings = UniqueSettings.from_env_auto_with_sdk_init()
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    # Initialize services from event
    chat_service = ChatService(event)
    kb_service = KnowledgeBaseService.from_event(event)
    latex_formula_string = create_latex_formula_string(
        latex_expression=r"\int_{a}^{b} f(x) \, dx"
    )
    chat_service.create_assistant_message(
        content=f"Here is a latex formula: {latex_formula_string}",
    )
    chat_service.free_user_input()
