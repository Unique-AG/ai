import json
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from unique_toolkit._common.exception import ConfigurationException

if TYPE_CHECKING:
    from fastapi import FastAPI, Request, status
    from fastapi.responses import JSONResponse
else:
    try:
        from fastapi import FastAPI, Request, status
        from fastapi.responses import JSONResponse
    except ImportError:
        FastAPI = None  # type: ignore[assignment, misc]
        Request = None  # type: ignore[assignment, misc]
        status = None  # type: ignore[assignment, misc]
        JSONResponse = None  # type: ignore[assignment, misc]

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueAuth, UniqueSettings

logger = getLogger(__name__)


def default_event_handler(event: Any) -> int:
    if status is None:
        return 200
    return status.HTTP_200_OK


def build_unique_custom_app(
    *,
    title: str = "Unique Chat App",
    webhook_path: str = "/webhook",
    settings_file: Path | None = None,
    chat_event_handler: Callable[[ChatEvent], int] = default_event_handler,
) -> "FastAPI":
    """Factory class for creating FastAPI apps with Unique webhook handling."""
    if FastAPI is None:
        raise ImportError(
            "FastAPI is not installed. Install it with: poetry install --with fastapi"
        )

    app = FastAPI(title=title)

    @app.get(path="/")
    async def health_check() -> JSONResponse:
        """Health check endpoint."""
        return JSONResponse(content={"status": "healthy", "service": title})

    @app.post(path=webhook_path)
    async def webhook_handler(request: Request) -> JSONResponse:
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

        if settings_file is not None:
            settings = UniqueSettings.from_env(env_file=settings_file)
        else:
            settings = UniqueSettings.from_env()

        # Verify webhook signature
        from unique_toolkit.app.webhook import is_webhook_signature_valid

        if not is_webhook_signature_valid(
            headers=headers,
            payload=body,
            endpoint_secret=settings.app.endpoint_secret.get_secret_value(),
        ):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid webhook signature"},
            )

        try:
            event_data = json.loads(body.decode(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing event: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": f"Invalid event format: {str(e)}"},
            )

        # Parse and route event
        event_name: str | None = event_data.get("event", None)
        from unique_toolkit.app.schemas import EventName

        try:
            match event_name:
                case EventName.EXTERNAL_MODULE_CHOSEN:
                    chat_event = ChatEvent.model_validate(event_data)

                    settings.auth = UniqueAuth.from_event(chat_event)
                    settings.init_sdk()

                    if chat_event.filter_event(
                        filter_options=settings.chat_event_filter_options
                    ):
                        return JSONResponse(
                            status_code=status.HTTP_200_OK,
                            content={"error": "Event filtered out"},
                        )

                    return_value = chat_event_handler(chat_event)
                    settings.auth = UniqueAuth()  # Reset auth to default
                    return JSONResponse(
                        content={"status": "success", "return_value": return_value}
                    )

                case _:
                    logger.error(f"Invalid event name: {event_name}")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"error": f"Invalid event name: {event_name}"},
                    )

        except ConfigurationException as e:
            logger.error(f"Configuration error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": f"Configuration error: {str(e)}"},
            )
        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": f"Error handling event: {str(e)}"},
            )

    return app
