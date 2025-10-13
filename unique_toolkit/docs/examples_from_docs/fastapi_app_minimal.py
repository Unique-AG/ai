import json
import logging
from typing import Callable, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

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

def default_event_handler(event:Any)->None:
    return None   

class UniqueAppFactory:
    """Factory class for creating FastAPI apps with Unique webhook handling."""
    
    def __init__(self, settings: UniqueSettings):
        """
        Initialize the app factory with shared configuration.
        
        Args:
            settings: UniqueSettings instance with API and app configuration
        """
        self._settings = settings
    
    @property
    def settings(self) -> UniqueSettings:
        """Get the UniqueSettings instance."""
        return self._settings
    
    def create_app(
        self,
        *,
        chat_event_handler: Callable[[ChatEvent], None] = default_event_handler,
        app_title: str = "Unique Chat App",
    ) -> FastAPI:
        """
        Create a FastAPI application with app-specific configuration.
        
        Args:
            chat_event_handler: Function that processes ChatEvent
            app_title: Title for the FastAPI app (shown in docs)
        
        Returns:
            Configured FastAPI application ready to receive webhooks
        """
        app = FastAPI(title=app_title)
        settings = self._settings
        
        @app.get("/")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "service": app_title}
        
        @app.post("/webhook")
        async def webhook_handler(request: Request):
            """
            Webhook endpoint for receiving events from Unique platform.
            
            This endpoint:
            1. Verifies the webhook signature
            2. Constructs a ChatEvent from the payload
            3. Calls the configured event handler
            """
            # Get raw body and headers
            body = await request.body()
            headers = dict(request.headers)

            # Verify webhook signature
            from unique_toolkit.app.webhook import is_webhook_signature_valid
            if not is_webhook_signature_valid(headers, body, settings.app.endpoint_secret.get_secret_value()):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"error": "Invalid webhook signature"},
                )

            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception as e:
                logger.error(f"Error parsing event: {e}", exc_info=True)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": f"Invalid event format: {str(e)}"},
                )

            # Parse and route event
            event_name: str | None = payload.get("event", None)
            from unique_toolkit.app.schemas import EventName

            match event_name:
                case EventName.USER_MESSAGE_CREATED | EventName.EXTERNAL_MODULE_CHOSEN:
                    event = ChatEvent.model_validate(payload)
                    return_value = chat_event_handler(event)
                    return {"status": "success", "return_value": return_value}
                case _:
                    logger.error(f"Invalid event name: {event_name}")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"error": f"Invalid event name: {event_name}"},
                    )
        
        return app


# Default event handler
def chat_event_handler(event: ChatEvent) -> None:
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


# Create the default app instance at module level
# This MUST be at module level so uvicorn can find it when importing
from pathlib import Path

# Initialize settings
_SETTINGS = UniqueSettings.from_env(env_file=Path(__file__).parent / "unique.env")
_SETTINGS.init_sdk()

# Create app using factory
factory = UniqueAppFactory(_SETTINGS)
_MINIMAL_APP = factory.create_app(
    chat_event_handler=chat_event_handler,
    app_title="Unique Minimal Chat App",
)


if __name__ == "__main__":
    import logging
    import uvicorn
    
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

