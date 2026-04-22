from logging import getLogger

from typing_extensions import override

from unique_toolkit._common.token import count_tokens
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.experimental.retrieve_search_scope_tool.config import (
    DisplayMode,
    RetrieveSearchScopeConfig,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.content.schemas import ContentInfo
from unique_toolkit.language_model.schemas import LanguageModelFunction
from unique_toolkit.services.factory import UniqueServiceFactory
from unique_toolkit.services.knowledge_base import KnowledgeBaseService

_LOGGER = getLogger(__name__)

_OPENABLE_MIME_PREFIXES = (
    "application/pdf",
    "application/msword",
    "application/vnd.ms-word",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.wordprocessingml",
    "application/vnd.openxmlformats-officedocument.presentationml",
)


class RetrieveSearchScopeTool(Tool[RetrieveSearchScopeConfig]):
    name = "RetrieveSearchScope"
    default_display_name = "Retrieve Search Scope"

    @override
    def display_name(self) -> str:
        return self.settings.display_name or self.default_display_name

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters={"type": "object", "properties": {}},
        )

    @override
    def tool_description_for_system_prompt(self) -> str:
        prompt = self.config.tool_description_for_system_prompt
        if self.config.display_mode == DisplayMode.tree:
            prompt = prompt.replace(
                "Returns all file names that are in the currently searchable knowledge base.",
                "Returns a folder tree of all files in the currently searchable knowledge base, "
                "showing how they are nested in the directory structure.",
            )
        return prompt

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []

    async def _has_prior_response_in_history(self) -> bool:
        """Check chat history for an existing RetrieveSearchScope tool response."""
        # TODO(UN-18756 #6): When tool-call persistence is introduced, verify
        # that the persisted response carries role="tool" and name="RetrieveSearchScope",
        # then replace getattr with direct attribute access or adapt to the actual schema.
        try:
            history = await self._chat_service.get_full_history_async()
            for msg in history:
                if msg.role.value == "tool" and getattr(msg, "name", None) == self.name:
                    return True
        except Exception:
            _LOGGER.debug(
                "Could not check history for prior tool response", exc_info=True
            )
        return False

    @staticmethod
    def _format_entry(ci: ContentInfo, prefix: str = "") -> str:
        if ci.mime_type.startswith(_OPENABLE_MIME_PREFIXES) and ci.id:
            name_part = f"{ci.key} ({ci.id})"
        else:
            name_part = ci.key
        return f"{prefix}/{name_part}" if prefix else name_part

    async def _build_flat_entries(self, kb_service: KnowledgeBaseService) -> list[str]:
        content_infos = await kb_service.get_content_infos_async(
            metadata_filter=kb_service._metadata_filter,
        )
        return [self._format_entry(ci) for ci in content_infos]

    async def _build_tree_entries(self, kb_service: KnowledgeBaseService) -> list[str]:
        resolved = await kb_service.resolve_visible_file_paths_async(
            metadata_filter=kb_service._metadata_filter,
        )
        entries: list[str] = []
        for ci, path_segments in resolved:
            folder_path = "/".join(
                seg for seg in path_segments[:-1] if seg != "_no_folder_path"
            )
            entries.append(self._format_entry(ci, prefix=folder_path))
        return entries

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        if await self._has_prior_response_in_history():
            return ToolCallResponse(
                id=tool_call.id or "unknown_id",
                name=self.name,
                content="RetrieveSearchScope has already been called in this conversation. "
                "Refer to the earlier result.",
            )

        try:
            settings = UniqueSettings.from_chat_event(self._event)
            kb_service = UniqueServiceFactory(
                settings=settings
            ).knowledge_base_service()

            if self.config.display_mode == DisplayMode.tree:
                raw_entries = await self._build_tree_entries(kb_service)
            else:
                raw_entries = await self._build_flat_entries(kb_service)
        except Exception:
            _LOGGER.exception("Failed to retrieve content infos from knowledge base")
            return ToolCallResponse(
                id=tool_call.id or "unknown_id",
                name=self.name,
                error_message="Failed to retrieve file list from the knowledge base.",
            )

        total_files = len(raw_entries)
        if total_files == 0:
            return ToolCallResponse(
                id=tool_call.id or "unknown_id",
                name=self.name,
                content="No files found in the search scope.",
            )

        max_input_tokens = self.config.language_model_max_input_tokens
        if max_input_tokens is None:
            _LOGGER.warning("language_model_max_input_tokens not set")
            return ToolCallResponse(
                id=tool_call.id or "unknown_id",
                name=self.name,
                error_message="Max_input_tokens not set.",
            )

        token_budget = int(
            max_input_tokens * self.config.context_window_fraction_for_file_list
        )
        token_count = 0
        seen: set[str] = set()
        display_entries: list[str] = []
        for entry in raw_entries:
            if entry in seen:
                continue
            seen.add(entry)

            # Uses default cl100k_base tokenizer (not model-specific). Acceptable
            # for short file names where the difference is negligible.
            entry_tokens = count_tokens(entry)
            if token_count + entry_tokens > token_budget:
                break
            display_entries.append(entry)
            token_count += entry_tokens

        if not display_entries:
            content = "Token limit to low to display search scope."
        else:
            omitted = total_files - len(display_entries)
            file_list = "\n".join(display_entries)
            content = (
                f"Listing {len(display_entries)} of {total_files} files in search scope"
            )
            if omitted > 0:
                content += f" ({omitted} omitted due to token budget or deduplication)"
            content += f":\n\n{file_list}"

        return ToolCallResponse(
            id=tool_call.id or "unknown_id",
            name=self.name,
            content=content,
        )


ToolFactory.register_tool(RetrieveSearchScopeTool, RetrieveSearchScopeConfig)
