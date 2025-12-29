import json
from logging import getLogger
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from pydantic import ValidationError

if TYPE_CHECKING:
    from fastapi import BackgroundTasks, FastAPI, Request, status
    from fastapi.responses import JSONResponse
else:
    try:
        from fastapi import BackgroundTasks, FastAPI, Request, status
        from fastapi.responses import JSONResponse
    except ImportError:
        FastAPI = None  # type: ignore[assignment, misc]
        Request = None  # type: ignore[assignment, misc]
        status = None  # type: ignore[assignment, misc]
        JSONResponse = None  # type: ignore[assignment, misc]
        BackgroundTasks = None  # type: ignore[assignment, misc]

from unique_toolkit.agentic_table.schemas import MagicTableEvent, MagicTableEventTypes
from unique_toolkit.app.schemas import BaseEvent, ChatEvent, EventName
from unique_toolkit.app.unique_settings import UniqueSettings

logger = getLogger(__name__)


def default_event_handler(event: Any) -> int:
    logger.info("Event received at event handler")
    if status is not None:
        return status.HTTP_200_OK
    else:
        # No fastapi installed
        return 200


T = TypeVar("T", bound=BaseEvent)


def build_unique_custom_app(
    *,
    title: str = "Unique Chat App",
    webhook_path: str = "/webhook",
    settings: UniqueSettings,
    event_handler: Callable[[T], int] = default_event_handler,
    event_constructor: Callable[..., T] = ChatEvent,
    subscribed_event_names: list[str] | None = None,
) -> "FastAPI":
    """Factory class for creating FastAPI apps with Unique webhook handling."""
    if FastAPI is None:
        raise ImportError(
            "FastAPI is not installed. Install it with: poetry install --with fastapi"
        )

    app = FastAPI(title=title)

    if subscribed_event_names is None:
        subscribed_event_names = [EventName.EXTERNAL_MODULE_CHOSEN]

    @app.get(path="/")
    async def health_check() -> JSONResponse:
        """Health check endpoint."""
        return JSONResponse(content={"status": "healthy", "service": title})

    @app.post(path=webhook_path)
    async def webhook_handler(
        request: Request, background_tasks: BackgroundTasks
    ) -> JSONResponse:
        """
        Webhook endpoint for receiving events from Unique platform.

        This endpoint:
        1. Verifies the webhook signature
        2. Constructs an event from the payload
        3. Calls the configured event handler
        """
        # Get raw body and headers
        body = await request.body()
        headers = dict(request.headers)

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
                content={"error": f"Invalid event format: {e.msg}"},
            )

        if event_data["event"] not in subscribed_event_names:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Not subscribed event"},
            )

        try:
            event = event_constructor(**event_data)
            if event.filter_event(filter_options=settings.chat_event_filter_options):
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"error": "Event filtered out"},
                )
        except ValidationError as e:
            # pydantic errors https://docs.pydantic.dev/2.10/errors/errors/
            logger.error(f"Validation error with model: {e.json()}", exc_info=True)
            raise e
        except ValueError as e:
            logger.error(f"Error deserializing event: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid event"},
            )

        # Run the task in background so that we don't block for long running tasks
        background_tasks.add_task(event_handler, event)
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "Event received"}
        )

    return app


def build_agentic_table_custom_app(
    *,
    title: str = "Agentic Table App",
    webhook_path: str = "/webhook",
    settings: UniqueSettings,
    event_handler: Callable[[MagicTableEvent], int] = default_event_handler,
) -> "FastAPI":
    """Factory class for creating FastAPI apps with Agentic Table webhook handling."""
    return build_unique_custom_app(
        title=title,
        webhook_path=webhook_path,
        settings=settings,
        event_handler=event_handler,
        event_constructor=MagicTableEvent,
        subscribed_event_names=[ev.value for ev in MagicTableEventTypes],
    )
