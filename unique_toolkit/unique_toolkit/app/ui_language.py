"""The language the chat UI is shown in, for text a module writes to the chat."""

from enum import StrEnum
from typing import Any

from unique_toolkit.app.schemas import AssistantWebhookEvent, BaseEventPayload


class UiLanguage(StrEnum):
    """The languages the chat UI is available in."""

    EN = "en"
    DE = "de"
    FR = "fr"


def ui_language(event: AssistantWebhookEvent[Any, BaseEventPayload]) -> UiLanguage:
    """Read the chat UI language an event was sent from.

    Args:
        event (AssistantWebhookEvent): A chat or Agentic Table event.

    Returns:
        UiLanguage: The language in ``payload.ui_language``; English when it is
            missing or not a supported language.
    """
    value = event.payload.ui_language
    return UiLanguage(value) if value in UiLanguage else UiLanguage.EN
