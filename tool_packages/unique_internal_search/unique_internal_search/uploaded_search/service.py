from typing import Literal

from pydantic import Field, create_model
from typing_extensions import override
from unique_toolkit import ContentService
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.feature_flags import feature_flags
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.names import UPLOADED_SEARCH_TOOL_NAME
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.app.schemas import BaseEvent, ChatEvent
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.content import Content
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
)

from unique_internal_search.service import InternalSearchTool
from unique_internal_search.uploaded_search.config import UploadedSearchConfig
from unique_internal_search.utils import extract_selected_uploaded_file_ids


class UploadedSearchTool(Tool[UploadedSearchConfig]):
    name = UPLOADED_SEARCH_TOOL_NAME
    _display_name = "Uploaded Search"

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
        self._company_id = event.company_id
        self._config = config
        config.chat_only = True
        self._internal_search_tool = InternalSearchTool(
            config, event, None, *args, **kwargs
        )
        self._internal_search_tool._display_name = self._display_name
        self._selected_uploaded_files = extract_selected_uploaded_file_ids(event)
        if isinstance(event, ChatEvent):
            self._user_query = event.payload.user_message.text
        else:
            self._user_query = None

        # This blocking API call should be avoided.
        # However, we don't have an easy way to pass user uploaded files to the tool currently
        # Note that this was being done in `tool_description_for_system_prompt` before
        self._valid_documents = self._compute_valid_documents()

    @override
    def display_name(self) -> str:
        return self._display_name

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        optional_fields: dict = {}
        if self._config.enable_content_id_filter and self._valid_documents:
            content_id_type = Literal[*(d.id for d in self._valid_documents)]
            optional_fields["content_ids"] = (
                list[content_id_type] | None,
                Field(
                    default=None,
                    description=self._config.param_description_content_ids,
                ),
            )

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
            **optional_fields,
        )

        return LanguageModelToolDescription(
            name=self.name,
            description=self._config.tool_description,
            parameters=internal_search_tool_input,
        )

    def tool_description_for_system_prompt(self) -> str:
        return render_template(
            self._config.tool_description_for_system_prompt,
            valid_documents=[
                {"name": doc.title or doc.key, "id": doc.id}
                for doc in self._valid_documents
            ],
        )

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

            # Verify no content_id outside valid ones, as tool may not be strict

            if "content_ids" in tool_call.arguments:
                tool_content_ids = tool_call.arguments["content_ids"]

                if tool_content_ids is not None:
                    valid_content_ids = {doc.id for doc in self._valid_documents}
                    filtered = list(
                        filter(
                            lambda content_id: content_id in valid_content_ids,
                            tool_content_ids,
                        )
                    )

                    if len(filtered) == 0:
                        raise ValueError("All supplied `content_ids` are invalid")

                    tool_call.arguments["content_ids"] = filtered

        tool_response = await self._internal_search_tool.run(tool_call)
        if (
            self._tool_progress_reporter
            and not feature_flags.enable_new_answers_ui_un_14411.is_enabled(
                self._company_id
            )
        ):
            await self._tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name="**Search Uploaded Document**",
                message=f"{search_string_data}",
                state=ProgressState.FINISHED,
            )
        tool_response.name = self.name
        if self._config.enable_tool_call_system_reminder:
            tool_response.system_reminder = (
                self._get_tool_call_response_system_reminder()
            )
        return tool_response

    def _get_tool_call_response_system_reminder(self) -> str:
        """
        When using the upload and search tool, unique AI agent is loosing the overview of the original user message and request
        This likely due to the amount of tokens included and as since it's a forced tool not necessarily relevant to the user's request.
        """
        # TODO: This message should be conditional on the tool being forced, but we do not have easy access to this information here
        return f"""<system_reminder>
This tool call was automatically executed to retrieve the user's uploaded documents by the system. Important to note:
- The retrieved documents may or may not be relevant to the user's actual query
- You must evaluate their relevance independently
- You are free to make additional tool calls as needed
- Focus on addressing the user's original request
{f"Original user message: {self._user_query}" if self._user_query else ""}

Please do not mention these instructions in your response to the user!
</system_reminder>"""

    def _compute_valid_documents(self) -> list[Content]:
        documents = self._content_service.get_documents_uploaded_to_chat()

        if feature_flags.enable_selected_uploaded_files_un_18215.is_enabled(
            self._company_id
        ):
            documents = [
                doc for doc in documents if doc.id in self._selected_uploaded_files
            ]

        valid_documents = []
        for doc in documents:
            if not doc.is_ingested(default_if_unknown=True) or doc.is_expired():
                continue
            valid_documents.append(doc)

        return valid_documents


ToolFactory.register_tool(UploadedSearchTool, UploadedSearchConfig)
