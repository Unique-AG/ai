import asyncio
import json
import logging
from typing import Annotated, overload, override

from pydantic import BaseModel, Field, JsonValue, StringConstraints
from typing_extensions import deprecated

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.experimental.ask_user_tool.config import (
    AskUserToolConfig,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.service_resolution import resolve_tool_services
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.elicitation import (
    ElicitationCancelledException,
    ElicitationDeclinedException,
    ElicitationExpiredException,
    ElicitationMode,
)
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

_LOGGER = logging.getLogger(__name__)

MessageType = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ResponseSchemaType = dict[str, JsonValue]


class AskUserToolInput(BaseModel):
    message: MessageType
    response_schema: ResponseSchemaType


class AskUserTool(Tool[AskUserToolConfig]):
    name = "AskUser"
    DISPLAY_NAME = "Ask User"

    @overload
    def __init__(
        self,
        config: AskUserToolConfig,
        *,
        chat_service: ChatService,
        language_model_service: LanguageModelService,
        tool_progress_reporter: ToolProgressReporter | None = ...,
    ) -> None: ...

    @overload
    @deprecated(
        "Passing event is deprecated. Inject chat_service and language_model_service."
    )
    def __init__(
        self,
        config: AskUserToolConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = ...,
    ) -> None: ...

    def __init__(
        self,
        config: AskUserToolConfig,
        event: ChatEvent | None = None,
        tool_progress_reporter: ToolProgressReporter | None = None,
        *,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
    ) -> None:
        resolved = resolve_tool_services(
            event=event,
            chat_service=chat_service,
            language_model_service=language_model_service,
        )
        super().__init__(
            config,
            tool_progress_reporter=tool_progress_reporter,
            chat_service=resolved.chat_service,
            language_model_service=resolved.language_model_service,
            event=resolved.event,
        )
        self._lock = asyncio.Lock()

    @override
    def display_name(self) -> str:
        return self.DISPLAY_NAME

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        class AskUserToolInputWithDescriptions(AskUserToolInput):
            message: MessageType = Field(description=self.config.message_description)
            response_schema: ResponseSchemaType = Field(
                description=self.config.response_schema_description
            )

        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=AskUserToolInputWithDescriptions,
        )

    @override
    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    @override
    def is_capability(self) -> bool:
        return True

    @override
    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    @override
    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        return []

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        # When multiple elicitation calls are created, the frontend will render them one by one
        # We need to lock the execution of the tool so that the timeout starts when the user
        # actually sees the elicitation call
        async with self._lock:
            return await self._run(tool_call)

    async def _run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        params = AskUserToolInput.model_validate(tool_call.arguments)

        service = self.chat_service.elicitation

        _LOGGER.info("Creating elicitation request")

        created = await service.create_async(
            mode=ElicitationMode.FORM,
            message=params.message,
            tool_name=self.display_name(),
            json_schema=params.response_schema,
            expires_in_seconds=self.config.timeout_seconds,
        )

        _LOGGER.info("Elicitation request (id %s) successfully created", created.id)

        try:
            elicitation = await service.wait_for_response_async(
                elicitation_id=created.id,
                timeout_seconds=self.config.timeout_seconds,
                poll_interval_seconds=self.config.poll_interval_seconds,
            )
        except ElicitationDeclinedException:
            _LOGGER.info("Elicitation with id %s was declined", created.id)
            return ToolCallResponse(
                id=tool_call.id,
                name=self.name,
                content=self.config.declined_message,
            )
        except ElicitationCancelledException:
            _LOGGER.info("Elicitation with id %s was cancelled", created.id)
            return ToolCallResponse(
                id=tool_call.id,
                name=self.name,
                content=self.config.cancelled_message,
            )
        except ElicitationExpiredException:
            _LOGGER.info("Elicitation with id %s has expired", created.id)
            return ToolCallResponse(
                id=tool_call.id,
                name=self.name,
                content=self.config.expired_message,
            )

        _LOGGER.info("User responded to elicitation request")

        return ToolCallResponse(
            id=tool_call.id,
            name=self.name,
            content=json.dumps(elicitation.response_content, ensure_ascii=False),
        )
