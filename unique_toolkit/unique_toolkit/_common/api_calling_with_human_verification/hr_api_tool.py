from enum import StrEnum

from pydantic import BaseModel, Field

from unique_toolkit import LanguageModelToolDescription
from unique_toolkit.app.dev_util import ChatEvent
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessage,
)
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter

from .api_tool import EndpointTool, EndpointToolConfig


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HumanResourcesTicketData(BaseModel):
    title: str = Field(description="The title of the ticket")
    user_story: str = Field(description="The user story of the ticket")
    status: TicketStatus = Field(description="The new status of the ticket")
    priority: Priority = Field(description="The priority of the ticket")
    detailed_description: str = Field(
        description="A detailed description of the ticket",
    )


class HRTicketEndpointTool(EndpointTool):
    def __init__(
        self,
        config: EndpointToolConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ):
        super().__init__(
            config=config, event=event, tool_progress_reporter=tool_progress_reporter
        )

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name="hrticket_endpoint_tool",
            description="This tool is used to call the HR Ticket endpoint",
            parameters=HumanResourcesTicketData,
        )

    def tool_description_for_system_prompt(self) -> str:
        raise NotImplementedError

    def tool_format_information_for_system_prompt(self) -> str:
        return ""

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_tool_call_result_for_loop_history(
        self, tool_response: ToolCallResponse
    ) -> LanguageModelMessage:
        raise NotImplementedError

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        raise NotImplementedError
