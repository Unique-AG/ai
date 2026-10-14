from typing import TYPE_CHECKING

from unique_toolkit._common._lazy import install as _install

from .find_env_file import EnvFileNotFoundError as EnvFileNotFoundError
from .find_env_file import find_env_file as find_env_file
from .init_logging import init_logging as init_logging
from .init_sdk import get_endpoint_secret as get_endpoint_secret
from .init_sdk import init_sdk as init_sdk
from .performance.async_tasks import (
    run_async_tasks_parallel as run_async_tasks_parallel,
)
from .performance.async_wrapper import to_async as to_async
from .webhook import is_webhook_signature_valid as is_webhook_signature_valid

if TYPE_CHECKING:
    from .schemas import (
        BaseEvent as BaseEvent,
    )
    from .schemas import (
        ChatEvent as ChatEvent,
    )
    from .schemas import (
        ChatEventAdditionalParameters as ChatEventAdditionalParameters,
    )
    from .schemas import (
        ChatEventAssistantMessage as ChatEventAssistantMessage,
    )
    from .schemas import (
        ChatEventPayload as ChatEventPayload,
    )
    from .schemas import (
        ChatEventUserMessage as ChatEventUserMessage,
    )
    from .schemas import (
        Event as Event,
    )
    from .schemas import (
        EventAssistantMessage as EventAssistantMessage,
    )
    from .schemas import (
        EventName as EventName,
    )
    from .schemas import (
        EventPayload as EventPayload,
    )
    from .schemas import (
        EventUserMessage as EventUserMessage,
    )
    from .schemas import (
        McpReferenceMapping as McpReferenceMapping,
    )
    from .schemas import (
        McpServer as McpServer,
    )
    from .schemas import (
        McpTool as McpTool,
    )
    from .schemas import (
        UploadedFileInfo as UploadedFileInfo,
    )
    from .verification import (
        verify_signature_and_construct_event as verify_signature_and_construct_event,
    )

DOMAIN_NAME = "app"

_SCHEMA_EXPORTS = frozenset(
    {
        "BaseEvent",
        "ChatEvent",
        "ChatEventAdditionalParameters",
        "ChatEventAssistantMessage",
        "ChatEventPayload",
        "ChatEventUserMessage",
        "Event",
        "EventAssistantMessage",
        "EventName",
        "EventPayload",
        "EventUserMessage",
        "McpReferenceMapping",
        "McpServer",
        "McpTool",
        "UploadedFileInfo",
    }
)

_EXPORTS: dict[str, tuple[str, str]] = {
    **{name: ("unique_toolkit.app.schemas", name) for name in _SCHEMA_EXPORTS},
    "verify_signature_and_construct_event": (
        "unique_toolkit.app.verification",
        "verify_signature_and_construct_event",
    ),
}

__all__ = [
    "DOMAIN_NAME",
    "EnvFileNotFoundError",
    "find_env_file",
    "get_endpoint_secret",
    "init_logging",
    "init_sdk",
    "is_webhook_signature_valid",
    "run_async_tasks_parallel",
    "to_async",
    "verify_signature_and_construct_event",
    "BaseEvent",
    "ChatEvent",
    "ChatEventAdditionalParameters",
    "ChatEventAssistantMessage",
    "ChatEventPayload",
    "ChatEventUserMessage",
    "Event",
    "EventAssistantMessage",
    "EventName",
    "EventPayload",
    "EventUserMessage",
    "McpReferenceMapping",
    "McpServer",
    "McpTool",
    "UploadedFileInfo",
]

_install(globals(), _EXPORTS)
