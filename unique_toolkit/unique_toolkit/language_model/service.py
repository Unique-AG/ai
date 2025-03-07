import logging
from typing import Optional, Type

from pydantic import BaseModel
from typing_extensions import deprecated

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.schemas import BaseEvent, ChatEvent, Event
from unique_toolkit.language_model.constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
    DEFAULT_COMPLETE_TIMEOUT,
    DOMAIN_NAME,
)
from unique_toolkit.language_model.functions import (
    complete,
    complete_async,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelTool,
)

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")



class LanguageModelService:
    """
    Provides methods to interact with the Language Model by generating responses.

    Args:
        company_id (str | None, optional): The company identifier. Defaults to None.
        user_id (str | None, optional): The user identifier. Defaults to None.
        chat_id (str | None, optional): The chat identifier. Defaults to None.
        assistant_id (str | None, optional): The assistant identifier. Defaults to None.
    """

    def __init__(
        self,
        event: Event | BaseEvent | None = None,
        user_id: str | None = None,
        **kwargs # TODO: Remove kwargs once we deprectate company_id
    ):
        self._event = event
        self._company_id = kwargs.get("company_id", None)
        self._user_id = user_id
        self._chat_id = kwargs.get("chat_id", None)
        self._assistant_id = kwargs.get("assistant_id", None)

        if event:
            self._company_id = event.company_id
            self._user_id = event.user_id
            if isinstance(event, (ChatEvent, Event)):
                self._chat_id = event.payload.chat_id
                self._assistant_id = event.payload.assistant_id

    @property
    @deprecated(
        "assistant_id is deprecated and will be removed in a future version."
    )
    def assistant_id(self) -> str | None:
        return self._assistant_id
    
        
    @property
    @deprecated(
        "The user_id property is deprecated and will be removed in a future version."
    )
    def user_id(self) -> str | None:
        return self._user_id

    @property
    @deprecated(
        "The chat_id property is deprecated and will be removed in a future version."
    )
    def chat_id(self) -> str | None:
        return self._chat_id

    @property
    @deprecated(
        "The company_id property is deprecated and will be removed in a future version."
    )
    def company_id(self) -> str | None:
        """
        Get the company identifier.
        """
        return self._company_id

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

    def complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
        structured_output_model: Optional[Type[BaseModel]] = None,
        structured_output_enforce_schema: bool = False,
        other_options: Optional[dict] = None,
    ) -> LanguageModelResponse:
        """
        Calls the completion endpoint synchronously without streaming the response.
        """
        [company_id] = validate_required_values([self._company_id])

        return complete(
            company_id=company_id,
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
        tools: Optional[list[LanguageModelTool]] = None,
        structured_output_model: Optional[Type[BaseModel]] = None,
        structured_output_enforce_schema: bool = False,
        other_options: Optional[dict] = None,
    ) -> LanguageModelResponse:
        """
        Calls the completion endpoint asynchronously without streaming the response.
        """
        [company_id] = validate_required_values([self._company_id])

        return await complete_async(
            company_id=company_id,
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
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
        structured_output_model: Optional[Type[BaseModel]] = None,
        structured_output_enforce_schema: bool = False,
        other_options: Optional[dict] = None,
    ) -> LanguageModelResponse:
        """
        Calls the completion endpoint asynchronously without streaming the response.
        """

        return await complete_async(
            company_id=company_id,
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            other_options=other_options,
            structured_output_model=structured_output_model,
            structured_output_enforce_schema=structured_output_enforce_schema,
        )
