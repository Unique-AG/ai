from typing import TYPE_CHECKING, Any

from .cancellation import CancellationEvent as CancellationEvent
from .cancellation import CancellationWatcher as CancellationWatcher
from .constants import DOMAIN_NAME as DOMAIN_NAME
from .schemas import ChatMessage as ChatMessage
from .schemas import ChatMessageAssessment as ChatMessageAssessment
from .schemas import ChatMessageAssessmentLabel as ChatMessageAssessmentLabel
from .schemas import ChatMessageAssessmentStatus as ChatMessageAssessmentStatus
from .schemas import ChatMessageAssessmentType as ChatMessageAssessmentType
from .schemas import ChatMessageRole as ChatMessageRole
from .utils import (
    convert_chat_history_to_injectable_string as convert_chat_history_to_injectable_string,
)

if TYPE_CHECKING:
    from .service import ChatService as ChatService


def __getattr__(name: str) -> Any:
    # Lazy import to break the circular dependency:
    # chat/__init__ → chat/service → chat/deprecated/service → chat/functions → chat/__init__
    # ChatService here is the deprecated shim; the canonical path is
    # unique_toolkit.services.chat_service.ChatService.
    if name == "ChatService":
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from unique_toolkit.chat.service import ChatService

        # Cache in globals() per PEP 562: subsequent access resolves via
        # normal attribute lookup, never re-entering __getattr__ (and
        # never re-opening the non-thread-safe warnings.catch_warnings()).
        globals()["ChatService"] = ChatService
        return ChatService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
