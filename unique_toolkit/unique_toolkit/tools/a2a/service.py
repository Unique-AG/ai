from pydantic import Field, create_model
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion

from unique_toolkit.app import ChatEvent
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.language_model import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelToolDescription,
)
from unique_toolkit.tools.a2a.config import SubAgentToolConfig
from unique_toolkit.tools.a2a.memory import (
    get_sub_agent_short_term_memory_manager,
)
from unique_toolkit.tools.a2a.schema import (
    SubAgentShortTermMemorySchema,
    SubAgentToolInput,
)
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool import Tool
from unique_toolkit.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)

from tools.factory import ToolFactory


class SubAgentTool(Tool[SubAgentToolConfig]):
    name: str = "SubAgentTool"

    def __init__(
        self,
        configuration: SubAgentToolConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ):
        super().__init__(configuration, event, tool_progress_reporter)
        self._user_id = event.user_id
        self._company_id = event.company_id
        self.name = configuration.name

        self._short_term_memory_manager = get_sub_agent_short_term_memory_manager(
            company_id=self._company_id,
            user_id=self._user_id,
            chat_id=event.payload.chat_id,
            assistant_id=self.config.assistant_id,
        )

    def tool_description(self) -> LanguageModelToolDescription:
        tool_input_model_with_description = create_model(
            "SubAgentToolInput",
            user_message=(
                str,
                Field(description=self.config.param_description_sub_agent_user_message),
            ),
        )

        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=tool_input_model_with_description,
        )

    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    def tool_format_information_for_system_prompt(self) -> str:
        return self.config.tool_format_information_for_system_prompt

    def tool_description_for_user_prompt(self) -> str:
        return self.config.tool_description_for_user_prompt

    def tool_format_information_for_user_prompt(self) -> str:
        return self.config.tool_format_information_for_user_prompt

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        return []

    async def _get_chat_id(self) -> str | None:
        if not self.config.reuse_chat:
            return None

        if self.config.chat_id is not None:
            return self.config.chat_id

        # Check if there is a saved chat id in short term memory
        short_term_memory = await self._short_term_memory_manager.load_async()

        if short_term_memory is not None:
            return short_term_memory.chat_id

        return None

    async def _save_chat_id(self, chat_id: str) -> None:
        if not self.config.reuse_chat:
            return

        await self._short_term_memory_manager.save_async(
            SubAgentShortTermMemorySchema(chat_id=chat_id)
        )

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        tool_input = SubAgentToolInput.model_validate(tool_call.arguments)

        if self.tool_progress_reporter:
            await self.tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name=f"{self.name}",
                message=f"{tool_input.user_message}",
                state=ProgressState.RUNNING,
            )

        # Check if there is a saved chat id in short term memory
        chat_id = await self._get_chat_id()

        response = await send_message_and_wait_for_completion(
            user_id=self._user_id,
            assistant_id=self.config.assistant_id,
            company_id=self._company_id,
            text=tool_input.user_message,  # type: ignore
            chat_id=chat_id,  # type: ignore
            poll_interval=self.config.poll_interval,
            max_wait=self.config.max_wait,
        )

        if chat_id is None:
            await self._save_chat_id(response["chatId"])

        if response["text"] is None:
            raise ValueError("No response returned from sub agent")

        self._text = response["text"]
        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=tool_call.name,
            content=response["text"],
        )

    def get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
    ) -> LanguageModelMessage:
        return ToolCallResponse(
            id=tool_response.id,  # type: ignore
            name=tool_response.name,
            content=tool_response.content,
        )

ToolFactory.register_tool(SubAgentTool, SubAgentToolConfig)