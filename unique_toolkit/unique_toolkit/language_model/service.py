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
        company_id: str | None = None,
        user_id: str | None = None,
        chat_id: str | None = None,
        assistant_id: str | None = None,
    ):
        self._event = event
        self.company_id = company_id
        self.user_id = user_id
        self.chat_id = chat_id
        self.assistant_id = assistant_id

        if event:
            self.company_id = event.company_id
            self.user_id = event.user_id
            if isinstance(event, (ChatEvent, Event)):
                self.chat_id = event.payload.chat_id
                self.assistant_id = event.payload.assistant_id

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
        [company_id] = validate_required_values([self.company_id])

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
        [company_id] = validate_required_values([self.company_id])

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
