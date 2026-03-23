from logging import getLogger
from typing import Any

from pydantic import Field, create_model
from typing_extensions import override

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.language_model.schemas import LanguageModelFunction
from unique_toolkit.services.factory import UniqueServiceFactory

from unique_retrieve_search_scope.config import RetrieveSearchScopeConfig

_LOGGER = getLogger(__name__)


class RetrieveSearchScopeTool(Tool[RetrieveSearchScopeConfig]):
    name = "RetrieveSearchScope"

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        parameters = create_model(
            "RetrieveSearchScopeInput",
            metadata_filter=(
                dict[str, Any] | None,
                Field(
                    default=None,
                    description="Optional metadata filter to narrow the search scope.",
                ),
            ),
        )
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=parameters,
        )

    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        metadata_filter: dict[str, Any] | None = None
        if isinstance(tool_call.arguments, dict):
            metadata_filter = tool_call.arguments.get("metadata_filter")

        try:
            settings = UniqueSettings.from_chat_event(self.event)
            kb_service = UniqueServiceFactory(settings=settings).knowledge_base_service()

            space_filter = kb_service._metadata_filter
            if space_filter and metadata_filter:
                metadata_filter = {"and": [space_filter, metadata_filter]}
            elif space_filter:
                metadata_filter = space_filter

            content_infos = await kb_service.get_content_infos_async(
                metadata_filter=metadata_filter,
            )
        except Exception:
            _LOGGER.exception("Failed to retrieve content infos from knowledge base")
            return ToolCallResponse(
                id=tool_call.id or "unknown_id",
                name=self.name,
                error_message="Failed to retrieve file list from the knowledge base.",
            )

        file_names = sorted({ci.key for ci in content_infos})

        if not file_names:
            content = "No files found in the search scope."
        else:
            file_list = "\n".join(file_names)
            content = f"Found {len(file_names)} files in search scope:\n\n{file_list}"

        return ToolCallResponse(
            id=tool_call.id or "unknown_id",
            name=self.name,
            content=content,
        )


ToolFactory.register_tool(RetrieveSearchScopeTool, RetrieveSearchScopeConfig)
