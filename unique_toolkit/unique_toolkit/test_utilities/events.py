import random
import string
from datetime import datetime
from typing import TYPE_CHECKING

from unique_toolkit.app.schemas import (
    BaseEvent,
    ChatEvent,
    ChatEventAdditionalParameters,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)

if TYPE_CHECKING:
    from typing import Any

    from unique_toolkit.app.unique_settings import UniqueSettings


def generated_numeric_string(length: int) -> str:
    return "".join(random.choices(string.digits, k=length))


def generated_alphanumeric_string(length: int) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generated_chat_id() -> str:
    return f"chat_{generated_alphanumeric_string(16)}"


def generated_assistant_id() -> str:
    return f"assistant_{generated_alphanumeric_string(16)}"


def generated_user_message_id() -> str:
    return f"msg_{generated_alphanumeric_string(16)}"


class TestEventFactory:
    """Factory for creating test event objects with sensible defaults.

    Simplifies test setup by providing convenient methods to generate
    chat events, messages, and related objects for testing.
    """

    def __init__(self, settings: UniqueSettings | None = None) -> None:
        self._settings = settings

    def _get_user_id(self) -> str:
        if self._settings is None:
            return generated_numeric_string(16)
        else:
            return self._settings.auth.user_id.get_secret_value()

    def _get_company_id(self) -> str:
        if self._settings is None:
            return generated_numeric_string(16)
        else:
            return self._settings.auth.company_id.get_secret_value()

    def get_chat_event_user_message(
        self,
        text: str,
        *,
        created_at: datetime | None = None,
        language: str = "DE",
        original_text: str | None = None,
    ) -> ChatEventUserMessage:
        if created_at is None:
            created_at = datetime.now()

        return ChatEventUserMessage(
            id=generated_user_message_id(),
            text=text,
            original_text=original_text or text,
            created_at=created_at.isoformat(),
            language=language,
        )

    def get_chat_event_assistant_message(
        self, *, created_at: datetime | None = None
    ) -> ChatEventAssistantMessage:
        if created_at is None:
            created_at = datetime.now()

        return ChatEventAssistantMessage(
            id=generated_assistant_id(), created_at=created_at.isoformat()
        )

    def get_chat_event_additional_parameters(
        self,
        *,
        translate_to_language: str | None = None,
        content_id_to_translate: str | None = None,
    ) -> ChatEventAdditionalParameters:
        return ChatEventAdditionalParameters(
            translate_to_language=translate_to_language,
            content_id_to_translate=content_id_to_translate,
        )

    def get_base_event(
        self,
        *,
        event: EventName = EventName.EXTERNAL_MODULE_CHOSEN,
        user_id: str | None = None,
        company_id: str | None = None,
    ) -> BaseEvent:
        return BaseEvent(
            id=generated_alphanumeric_string(16),
            event=event,
            user_id=user_id or self._get_user_id(),
            company_id=company_id or self._get_company_id(),
        )

    def get_chat_event_payload(
        self,
        *,
        name: str,
        description: str,
        user_message_text: str,
        user_message_created_at: datetime | None = None,
        user_message_language: str = "DE",
        user_message_original_text: str | None = None,
        assistant_message_created_at: datetime | None = None,
        configuration: dict[str, Any] | None = None,
        chat_id: str | None = None,
        assistant_id: str | None = None,
    ) -> ChatEventPayload:
        if chat_id is None:
            chat_id = generated_chat_id()

        if assistant_id is None:
            assistant_id = generated_assistant_id()

        assistant_message = self.get_chat_event_assistant_message(
            created_at=assistant_message_created_at or datetime.now()
        )
        user_message = self.get_chat_event_user_message(
            text=user_message_text,
            created_at=user_message_created_at or datetime.now(),
            language=user_message_language,
            original_text=user_message_original_text,
        )
        return ChatEventPayload(
            name=name,
            description=description,
            configuration=configuration or {},
            chat_id=chat_id,
            assistant_id=assistant_id,
            user_message=user_message,
            assistant_message=assistant_message,
        )

    def get_chat_event(
        self,
        *,
        name: str,
        event_name: EventName = EventName.EXTERNAL_MODULE_CHOSEN,
        description: str,
        user_message_text: str,
        user_message_created_at: datetime = datetime.now(),
        user_message_language: str = "DE",
        user_message_original_text: str | None = None,
        assistant_message_created_at: datetime | None = None,
        configuration: dict[str, Any] | None = None,
        chat_id: str = generated_chat_id(),
        assistant_id: str = generated_assistant_id(),
        user_id: str | None = None,
        company_id: str | None = None,
        version: str = "1.0",
    ) -> ChatEvent:
        payload = self.get_chat_event_payload(
            name=name,
            description=description,
            user_message_text=user_message_text,
            user_message_created_at=user_message_created_at,
            user_message_language=user_message_language,
            user_message_original_text=user_message_original_text,
            assistant_message_created_at=assistant_message_created_at,
            configuration=configuration or {},
            chat_id=chat_id,
            assistant_id=assistant_id,
        )
        return ChatEvent(
            id=generated_alphanumeric_string(16),
            event=event_name,
            user_id=user_id or self._get_user_id(),
            company_id=company_id or self._get_company_id(),
            payload=payload,
            created_at=int(datetime.now().timestamp()),
            version=version,
        )
