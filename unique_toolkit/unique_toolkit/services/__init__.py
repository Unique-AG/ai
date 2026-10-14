from typing import TYPE_CHECKING

from unique_toolkit._common._lazy import install as _install

if TYPE_CHECKING:
    from unique_toolkit.app.unique_settings import AuthContext as AuthContext
    from unique_toolkit.app.unique_settings import ChatContext as ChatContext
    from unique_toolkit.app.unique_settings import UniqueContext as UniqueContext
    from unique_toolkit.services.chat_service import ChatService as ChatService
    from unique_toolkit.services.factory import (
        ServiceNotRegisteredError as ServiceNotRegisteredError,
    )
    from unique_toolkit.services.factory import (
        UniqueServiceFactory as UniqueServiceFactory,
    )
    from unique_toolkit.services.knowledge_base import (
        KnowledgeBaseService as KnowledgeBaseService,
    )

_EXPORTS: dict[str, tuple[str, str]] = {
    "AuthContext": ("unique_toolkit.app.unique_settings", "AuthContext"),
    "ChatContext": ("unique_toolkit.app.unique_settings", "ChatContext"),
    "ChatService": ("unique_toolkit.services.chat_service", "ChatService"),
    "KnowledgeBaseService": (
        "unique_toolkit.services.knowledge_base",
        "KnowledgeBaseService",
    ),
    "ServiceNotRegisteredError": (
        "unique_toolkit.services.factory",
        "ServiceNotRegisteredError",
    ),
    "UniqueContext": ("unique_toolkit.app.unique_settings", "UniqueContext"),
    "UniqueServiceFactory": (
        "unique_toolkit.services.factory",
        "UniqueServiceFactory",
    ),
}

__all__ = list(_EXPORTS)

_install(globals(), _EXPORTS)
