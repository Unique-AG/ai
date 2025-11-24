
import logging
from pathlib import Path
from unique_toolkit.app.fast_api_factory import build_unique_custom_app
from unique_toolkit import (
    ChatService,
    KnowledgeBaseService,
    LanguageModelName,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
from unique_toolkit.app.schemas import ChatEvent
logger = logging.getLogger(__name__)


# Default event handler
def chat_event_handler(event: ChatEvent) -> int:
    """
    Default event handler that echoes back the user's message.
    
    This is a simple example that demonstrates:
    - Initializing services from the event
    - Building messages with OpenAIMessageBuilder
    - Using complete_with_references for AI responses
    """
    # Initialize services from event
    chat_service = ChatService(event)
    kb_service = KnowledgeBaseService.from_event(event)
    
    # Build messages
    messages = (
        OpenAIMessageBuilder()
        .system_message_append(content="You are a helpful assistant")
        .user_message_append(content=event.payload.user_message.text)
        .messages
    )
    
    # Complete with references
    chat_service.complete_with_references(
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4o_2024_1120,
    )

    return 0


# Create the default app instance at module level
# This MUST be at module level so uvicorn can find it when importing

# Create app using factory
_MINIMAL_APP = build_unique_custom_app(settings_file=Path(__file__).parent / "unique.env", 
                                                title="Unique Minimal Chat App", 
                                                chat_event_handler=chat_event_handler)


if __name__ == "__main__":
    import logging
    import uvicorn

    # Initialize settings
       
    # Enable debug logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    uvicorn.run(
        "fastapi_app_minimal:_MINIMAL_APP",
        host="0.0.0.0",
        port=5001,
        reload=True,
        log_level="debug",
    )

