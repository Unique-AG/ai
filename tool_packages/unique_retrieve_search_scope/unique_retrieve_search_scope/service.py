from logging import getLogger
from typing import Any

from pydantic import Field, create_model
from typing_extensions import override
from unique_toolkit._common.token import count_tokens
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.schemas import LanguageModelFunction
from unique_toolkit.services.factory import UniqueServiceFactory

from unique_retrieve_search_scope.config import RetrieveSearchScopeConfig

_LOGGER = getLogger(__name__)


class RetrieveSearchScopeTool(Tool[RetrieveSearchScopeConfig]):
    name = "RetrieveSearchScope"
    default_display_name = "Retrieve Search Scope"

    @override
    def display_name(self) -> str:
        return self.settings.display_name or self.default_display_name

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

    async def _has_prior_response_in_history(self) -> bool:
        """Check chat history for an existing RetrieveSearchScope tool call with a response."""
        try:
            history = await self._chat_service.get_full_history_async()
            for msg in history:
                if msg.role.value == "assistant" and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.function.name == self.name:
                            return True
        except Exception:
            _LOGGER.debug("Could not check history for prior tool calls", exc_info=True)
        return False

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        if await self._has_prior_response_in_history():
            return ToolCallResponse(
                id=tool_call.id or "unknown_id",
                name=self.name,
                content="RetrieveSearchScope has already been called in this conversation. "
                "Refer to the earlier result.",
            )

        metadata_filter: dict[str, Any] | None = None
        if isinstance(tool_call.arguments, dict):
            metadata_filter = tool_call.arguments.get("metadata_filter")

        try:
            settings = UniqueSettings.from_chat_event(self._event)
            kb_service = UniqueServiceFactory(
                settings=settings
            ).knowledge_base_service()

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

        seen_keys: set[str] = set()
        unique_keys: list[str] = []
        for ci in content_infos:
            if ci.key not in seen_keys:
                seen_keys.add(ci.key)
                unique_keys.append(ci.key)

        display_entries = sorted(unique_keys)
        total_files = len(display_entries)

        try:
            model_name = self._event.payload.configuration.get("space", {}).get(
                "languageModel"
            )
            file_names: list[str] = []
            if model_name is not None:
                model_info = LanguageModelInfo.from_name(model_name)
                token_budget = int(
                    model_info.token_limits.token_limit_input
                    * self.config.context_window_fraction_for_file_list
                )
                token_count = 0
                for entry in display_entries:
                    entry_tokens = count_tokens(entry)
                    if token_count + entry_tokens > token_budget:
                        break
                    file_names.append(entry)
                    token_count += entry_tokens
            else:
                file_names = display_entries
        except Exception:
            _LOGGER.debug(
                "Token budget calculation failed, using full list", exc_info=True
            )
            file_names = display_entries

        if not file_names:
            content = "No files found in the search scope."
        else:
            omitted = total_files - len(file_names)
            file_list = "\n".join(file_names)
            content = (
                f"Listing {len(file_names)} of {total_files} files in search scope"
            )
            if omitted > 0:
                content += f" ({omitted} omitted due to token budget)"
            content += f":\n\n{file_list}"

        return ToolCallResponse(
            id=tool_call.id or "unknown_id",
            name=self.name,
            content=content,
        )


ToolFactory.register_tool(RetrieveSearchScopeTool, RetrieveSearchScopeConfig)
