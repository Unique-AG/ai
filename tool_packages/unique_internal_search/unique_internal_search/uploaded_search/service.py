from __future__ import annotations

from typing import TYPE_CHECKING, Literal, overload

from pydantic import Field, create_model
from typing_extensions import deprecated, override
from unique_toolkit import ContentService
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.feature_flags import feature_flags
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.names import UPLOADED_SEARCH_TOOL_NAME
from unique_toolkit.agentic.tools.run_context import ToolRunContext
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.service_resolution import resolve_tool_services
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.content import Content
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
)

from unique_internal_search.service import InternalSearchTool
from unique_internal_search.uploaded_search.config import UploadedSearchConfig

if TYPE_CHECKING:
    from unique_toolkit.language_model.service import LanguageModelService
    from unique_toolkit.services.chat_service import ChatService


class UploadedSearchTool(Tool[UploadedSearchConfig]):
    name = UPLOADED_SEARCH_TOOL_NAME
    _display_name = "Uploaded Search"
    _internal_search_tool: InternalSearchTool

    @overload
    def __init__(
        self,
        config: UploadedSearchConfig,
        *,
        chat_service: ChatService,
        language_model_service: LanguageModelService,
        tool_progress_reporter: ToolProgressReporter,
        event: ChatEvent | None = ...,
        content_service: ContentService | None = ...,
    ) -> None: ...

    @overload
    @deprecated(
        "Passing event is deprecated. Inject chat_service and language_model_service."
    )
    def __init__(
        self,
        config: UploadedSearchConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter,
    ) -> None: ...

    def __init__(
        self,
        config: UploadedSearchConfig,
        event: ChatEvent | None = None,
        tool_progress_reporter: ToolProgressReporter | None = None,
        *,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
        content_service: ContentService | None = None,
        run_context: ToolRunContext | None = None,
    ):
        self._config = config
        config.chat_only = True
        self._valid_documents: list[Content] = []
        self._selected_uploaded_files: list[str] = []
        self._user_query = ""

        resolved = resolve_tool_services(
            event=event,
            run_context=run_context,
            chat_service=chat_service,
            language_model_service=language_model_service,
            content_service=content_service,
        )
        if resolved.content_service is None:
            raise ValueError("UploadedSearchTool requires content_service")

        super().__init__(
            config,
            tool_progress_reporter=tool_progress_reporter,
            chat_service=resolved.chat_service,
            language_model_service=resolved.language_model_service,
            event=resolved.event,
            content_service=resolved.content_service,
        )
        self._run_context = resolved.run_context
        self._initialize_runtime_state()

    def _initialize_runtime_state(self) -> None:
        self._company_id = self._chat_service._company_id
        self._selected_uploaded_files = list(
            self._run_context.selected_uploaded_file_ids
        )
        self._user_query = self._chat_service._user_message_text or ""
        self._internal_search_tool = InternalSearchTool(
            self._config,
            chat_service=self._chat_service,
            language_model_service=self._language_model_service,
            tool_progress_reporter=self._tool_progress_reporter,
            content_service=self._content_service,
            run_context=self._run_context,
            display_name=self._display_name,
        )
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
        if self._content_service is None:
            raise ValueError("UploadedSearchTool requires injected content_service")
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
