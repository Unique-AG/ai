from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unique_toolkit.agentic.tools.run_context import ToolRunContext
    from unique_toolkit.app.schemas import ChatEvent
    from unique_toolkit.content.service import ContentService
    from unique_toolkit.language_model.service import LanguageModelService
    from unique_toolkit.services.chat_service import ChatService


@dataclass(frozen=True)
class ResolvedToolServices:
    chat_service: ChatService
    language_model_service: LanguageModelService
    content_service: ContentService | None
    run_context: ToolRunContext
    event: ChatEvent | None


def resolve_tool_services(
    *,
    event: ChatEvent | None = None,
    run_context: ToolRunContext | None = None,
    chat_service: ChatService | None = None,
    language_model_service: LanguageModelService | None = None,
    content_service: ContentService | None = None,
) -> ResolvedToolServices:
    """Resolve tool wiring: inject shared services or bootstrap missing ones from event.

    ``event`` is required only when neither ``chat_service`` nor
    ``language_model_service`` is supplied. Injected services are never rebuilt from
    ``event``. ``content_service`` falls back to ``ContentService.from_event(event)``
    when absent and ``event`` is available.

    ``run_context`` carries the per-turn snapshot (session config, file selection,
    etc.). When omitted but ``event`` is present it is built via
    ``ToolRunContext.from_chat_event``.
    """
    from unique_toolkit.agentic.tools.run_context import ToolRunContext

    if (chat_service is None) != (language_model_service is None):
        raise ValueError(
            "chat_service and language_model_service must be injected together; "
            "supplying only one is not supported."
        )

    if chat_service is None:
        if event is None:
            raise ValueError(
                "event or injected chat_service and language_model_service is required"
            )
        from unique_toolkit.language_model.service import LanguageModelService
        from unique_toolkit.services.chat_service import ChatService

        chat_service = ChatService(event)
        language_model_service = LanguageModelService.from_event(event)

    if run_context is None:
        if event is not None:
            run_context = ToolRunContext.from_chat_event(event)
        else:
            run_context = ToolRunContext()

    if content_service is None and event is not None:
        from unique_toolkit.content.service import ContentService

        content_service = ContentService.from_event(event)

    assert chat_service is not None
    assert language_model_service is not None

    return ResolvedToolServices(
        chat_service=chat_service,
        language_model_service=language_model_service,
        content_service=content_service,
        run_context=run_context,
        event=event,
    )
