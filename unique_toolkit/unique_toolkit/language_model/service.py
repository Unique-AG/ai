import logging
from typing import Any, Optional, Type, overload

from pydantic import BaseModel
from typing_extensions import deprecated

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.schemas import BaseEvent, ChatEvent, Event
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
    DEFAULT_COMPLETE_TIMEOUT,
    DOMAIN_NAME,
)
from unique_toolkit.language_model.functions import (
    complete,
    complete_async,
    complete_with_references,
    complete_with_references_async,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelTool,
    LanguageModelToolDescription,
)

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


class LanguageModelService:
    """
    Provides methods to interact with the Language Model by generating responses.
    """

    @deprecated(
        "Use __init__ with company_id and user_id instead or use the classmethod `from_event`"
    )
    @overload
    def __init__(self, event: Event | ChatEvent | BaseEvent): ...

    """
        Initialize the LanguageModelService with an event (deprecated)
    """

    @overload
    def __init__(self, *, company_id: str, user_id: str): ...

    """
        Initialize the LanguageModelService with a company_id and user_id.
    """

    def __init__(
        self,
        event: Event | ChatEvent | BaseEvent | None = None,
        company_id: str | None = None,
        user_id: str | None = None,
        **kwargs: dict[str, Any],  # only here for backward compatibility
    ):
        if isinstance(event, (ChatEvent, Event)):
            self._event = event
            self._chat_id: str | None = event.payload.chat_id
            self._assistant_id: str | None = event.payload.assistant_id
            self._company_id = event.company_id
            self._user_id = event.user_id
            if isinstance(event, (ChatEvent, Event)):
                self._chat_id = event.payload.chat_id
                self._assistant_id = event.payload.assistant_id
        elif isinstance(event, BaseEvent):
            self._event = event
            self._company_id = event.company_id
            self._user_id = event.user_id
            self._chat_id: str | None = None
            self._assistant_id: str | None = None
        else:
            [company_id, user_id] = validate_required_values([company_id, user_id])
            self._event = None
            self._company_id: str = company_id
            self._user_id: str = user_id
            self._chat_id: str | None = None
            self._assistant_id: str | None = None

    @classmethod
    def from_event(cls, event: BaseEvent):
        """
        Initialize the LanguageModelService with an event.
        """
        return cls(company_id=event.company_id, user_id=event.user_id)

    @classmethod
    def from_settings(cls, settings: UniqueSettings | None = None):
        """
        Initialize the LanguageModelService with a settings object.
        If the settings object is not provided, it will be initialized from the environment.
        """
        if settings is None:
            settings = UniqueSettings.from_env_auto_with_sdk_init()

        return cls(
            company_id=settings.auth.company_id.get_secret_value(),
            user_id=settings.auth.user_id.get_secret_value(),
        )

    @property
    @deprecated(
        "The event property is deprecated and will be removed in a future version."
    )
    def event(self) -> Event | BaseEvent | None:
        """
        Get the event object (deprecated).

        Returns:
            Event | BaseEvent | None: The event object.
        """
        return self._event

    @property
    @deprecated(
        "The company_id property is deprecated and will be removed in a future version."
    )
    def company_id(self) -> str | None:
        """
        Get the company identifier (deprecated).

        Returns:
            str | None: The company identifier.
        """
        return self._company_id

    @company_id.setter
    @deprecated(
        "The company_id setter is deprecated and will be removed in a future version."
    )
    def company_id(self, value: str) -> None:
        """
        Set the company identifier (deprecated).

        Args:
            value (str | None): The company identifier.
        """
        self._company_id = value

    @property
    @deprecated(
        "The user_id property is deprecated and will be removed in a future version."
    )
    def user_id(self) -> str | None:
        """
        Get the user identifier (deprecated).

        Returns:
            str | None: The user identifier.
        """
        return self._user_id

    @user_id.setter
    @deprecated(
        "The user_id setter is deprecated and will be removed in a future version."
    )
    def user_id(self, value: str) -> None:
        """
        Set the user identifier (deprecated).

        Args:
            value (str | None): The user identifier.
        """
        self._user_id = value

    @property
    @deprecated(
        "The chat_id property is deprecated and will be removed in a future version."
    )
    def chat_id(self) -> str | None:
        """
        Get the chat identifier (deprecated).

        Returns:
            str | None: The chat identifier.
        """
        return self._chat_id

    @chat_id.setter
    @deprecated(
        "The chat_id setter is deprecated and will be removed in a future version."
    )
    def chat_id(self, value: str | None) -> None:
        """
        Set the chat identifier (deprecated).

        Args:
            value (str | None): The chat identifier.
        """
        self._chat_id = value

    @property
    @deprecated(
        "The assistant_id property is deprecated and will be removed in a future version."
    )
    def assistant_id(self) -> str | None:
        """
        Get the assistant identifier (deprecated).

        Returns:
            str | None: The assistant identifier.
        """
        return self._assistant_id

    @assistant_id.setter
    @deprecated(
        "The assistant_id setter is deprecated and will be removed in a future version."
    )
    def assistant_id(self, value: str | None) -> None:
        """
        Set the assistant identifier (deprecated).

        Args:
            value (str | None): The assistant identifier.
        """
        self._assistant_id = value

    def complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool | LanguageModelToolDescription]] = None,
        structured_output_model: Optional[Type[BaseModel]] = None,
        structured_output_enforce_schema: bool = False,
        other_options: Optional[dict] = None,
    ) -> LanguageModelResponse:
        """
        Calls the completion endpoint synchronously without streaming the response.
        """

        return complete(
            company_id=self._company_id,
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            other_options=other_options,
            structured_output_model=structured_output_model,
            structured_output_enforce_schema=structured_output_enforce_schema,
        )

    async def complete_async(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool | LanguageModelToolDescription]] = None,
        structured_output_model: Optional[Type[BaseModel]] = None,
        structured_output_enforce_schema: bool = False,
        other_options: Optional[dict] = None,
    ) -> LanguageModelResponse:
        """
        Calls the completion endpoint asynchronously without streaming the response.
        """

        return await complete_async(
            company_id=self._company_id,
            user_id=self._user_id,
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            other_options=other_options,
            structured_output_model=structured_output_model,
            structured_output_enforce_schema=structured_output_enforce_schema,
        )

    @classmethod
    @deprecated("Use complete_async of language_model.functions instead")
    async def complete_async_util(
        cls,
        company_id: str,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        user_id: str | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool | LanguageModelToolDescription]] = None,
        structured_output_model: Optional[Type[BaseModel]] = None,
        structured_output_enforce_schema: bool = False,
        other_options: Optional[dict] = None,
    ) -> LanguageModelResponse:
        """
        Calls the completion endpoint asynchronously without streaming the response.
        """

        return await complete_async(
            company_id=company_id,
            user_id=user_id,
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            other_options=other_options,
            structured_output_model=structured_output_model,
            structured_output_enforce_schema=structured_output_enforce_schema,
        )

    def complete_with_references(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict = {},
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
        start_text: str | None = None,
        other_options: dict[str, Any] | None = None,
    ) -> LanguageModelStreamResponse:
        return complete_with_references(
            company_id=self._company_id,
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            temperature=temperature,
            timeout=timeout,
            other_options=other_options,
            tools=tools,
            start_text=start_text,
        )

    async def complete_with_references_async(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict = {},
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: list[LanguageModelTool | LanguageModelToolDescription] | None = None,
        start_text: str | None = None,
        other_options: dict[str, Any] | None = None,
    ) -> LanguageModelStreamResponse:
        return await complete_with_references_async(
            company_id=self._company_id,
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            temperature=temperature,
            timeout=timeout,
            other_options=other_options,
            tools=tools,
            start_text=start_text,
        )
