from pydantic import Field, create_model
from typing_extensions import override
from unique_toolkit import ContentService
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.app.schemas import BaseEvent
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
)

from unique_internal_search.service import InternalSearchTool
from unique_internal_search.uploaded_search.config import UploadedSearchConfig


class UploadedSearchTool(Tool[UploadedSearchConfig]):
    name = "UploadedSearch"

    def __init__(
        self,
        config: UploadedSearchConfig,
        event: BaseEvent,
        tool_progress_reporter: ToolProgressReporter,
        *args,
        **kwargs,
    ):
        self._tool_progress_reporter = tool_progress_reporter
        self._content_service = ContentService.from_event(event)
        self._config = config
        config.chat_only = True
        self._internal_search_tool = InternalSearchTool(
            config, event, None, *args, **kwargs
        )

    async def post_progress_message(
        self, message: str, tool_call: LanguageModelFunction, **kwargs
    ):
        if self._tool_progress_reporter:
            await self._tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name="**Search Uploaded Document**",
                message=message,
                state=ProgressState.RUNNING,
            )

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        internal_search_tool_input = create_model(
            "InternalSearchToolInput",
            search_string=(
                str,
                Field(description=self._config.param_description_search_string),
            ),
            language=(
                str,
                Field(description=self._config.param_description_language),
            ),
        )
        return LanguageModelToolDescription(
            name=self.name,
            description=self._config.tool_description,
            parameters=internal_search_tool_input,
        )

    def tool_description_for_system_prompt(self) -> str:
        documents = self._content_service.get_documents_uploaded_to_chat()
        list_all_documents = "".join([f"- {doc.title or doc.key}" for doc in documents])
        return self._config.tool_description_for_system_prompt + list_all_documents

    def tool_format_information_for_system_prompt(self) -> str:
        return self._config.tool_format_information_for_system_prompt

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return self._config.evaluation_check_list

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        evaluation_check_list = self.evaluation_check_list()
        return evaluation_check_list

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        search_string_data = ""
        if isinstance(tool_call.arguments, dict):
            search_string_data = tool_call.arguments.get("search_string", "") or ""
        tool_response = await self._internal_search_tool.run(tool_call)
        if self._tool_progress_reporter:
            await self._tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name="**Search Uploaded Document**",
                message=f"{search_string_data}",
                state=ProgressState.FINISHED,
            )
        tool_response.name = self.name
        tool_response.tool_call_response_system_reminder = (
            self._get_tool_call_response_system_reminder()
        )
        return tool_response

    def _get_tool_call_response_system_reminder(self) -> str:
        """
        When using the upload and search tool, unique AI agent is loosing the overview of the original user message and request
        This likely due to the amount of tokens included and as since it's a forced tool not necessarily relevant to the user's request.
        """
        query = self._event.payload.user_message.text
        return f"""
            <system_reminder>
            This tool call was automatically executed to retrieve the user's uploaded documents. You did not initiate this call.
            IMPORTANT CONTEXT:
            - The retrieved documents may or may not be relevant to the user's actual query
            - You must evaluate their relevance independently
            - You are free to make additional tool calls as needed
            - Focus on addressing the user's original request
            {f"Original user message: {query}" if query else ""}
            </system_reminder>"""


ToolFactory.register_tool(UploadedSearchTool, UploadedSearchConfig)
