from logging import getLogger

from typing_extensions import override
from unique_toolkit import ShortTermMemoryService
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import (
    AgentChunksHandler,
    EvaluationMetricName,
    Tool,
)
from unique_toolkit.language_model import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelMessageRole,
)
from unique_toolkit.language_model.schemas import LanguageModelToolDescription
from unique_toolkit.services.knowledge_base import KnowledgeBaseService

from unique_swot.config import SwotAnalysisToolConfig
from unique_swot.services.citations import CitationManager
from unique_swot.services.collection import CollectionContext, SourceCollectionManager
from unique_swot.services.collection.registry import ContentChunkRegistry
from unique_swot.services.executor import SWOTExecutionManager
from unique_swot.services.memory.base import SwotMemoryService
from unique_swot.services.notifier import ProgressNotifier
from unique_swot.services.report import REPORT_TEMPLATE
from unique_swot.services.schemas import SWOTPlan

_LOGGER = getLogger(__name__)


class SwotAnalysisTool(Tool[SwotAnalysisToolConfig]):
    name = "SwotAnalysis"

    def __init__(self, configuration: SwotAnalysisToolConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)

        metadata_filter = self._event.payload.metadata_filter

        self._knowledge_base_service = KnowledgeBaseService.from_event(self._event)

        self._notifier = ProgressNotifier(
            chat_service=self._chat_service,
            message_id=self._event.payload.assistant_message.id,
        )

        _short_term_memory_service = ShortTermMemoryService(
            company_id=self._event.company_id,
            user_id=self._event.user_id,
            chat_id=self._event.payload.chat_id,
            message_id=None,
        )

        self._memory_service = SwotMemoryService(
            short_term_memory_service=_short_term_memory_service,
            knowledge_base_service=self._knowledge_base_service,
            cache_scope_id=configuration.cache_scope_id,
        )

        self._content_chunk_registry = ContentChunkRegistry(
            memory_service=self._memory_service
        )

        self._source_collection_manager = SourceCollectionManager(
            context=CollectionContext(
                use_earnings_calls=False,
                use_web_sources=False,
                metadata_filter=metadata_filter,
            ),
            knowledge_base_service=self._knowledge_base_service,
            content_chunk_registry=self._content_chunk_registry,
            notifier=self._notifier,
        )

        self._citation_manager = CitationManager(
            content_chunk_registry=self._content_chunk_registry,
        )

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=SWOTPlan,
        )

    @override
    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    @override
    def tool_format_information_for_system_prompt(self) -> str:
        return self.config.tool_format_information_for_system_prompt

    @override
    def tool_description_for_user_prompt(self) -> str:
        return self.config.tool_description_for_user_prompt

    @override
    def tool_format_information_for_user_prompt(self) -> str:
        return self.config.tool_format_information_for_user_prompt

    @override
    def tool_format_reminder_for_user_prompt(self) -> str:
        return self.config.tool_format_reminder_for_user_prompt

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        try:
            plan = SWOTPlan.model_validate(tool_call.arguments)
            # Ensure the plan is semantically valid for execution, as Pydantic validation may accept plans that
            # are structurally correct but logically invalid (e.g., missing required modify instructions)

            plan.validate_swot_plan()

            number_of_executions = (
                plan.get_number_of_executions() + 1
            )  # +1 for Collecting sources step

            self._notifier.start_progress(number_of_executions)

            # Get Sources
            sources = self._source_collection_manager.collect_sources()

            _LOGGER.info(f"Collected {len(sources)} sources!")

            total_steps = self._calculate_total_steps(plan, len(sources))
            _LOGGER.info(f"Total steps: {total_steps}")
            executor = SWOTExecutionManager(
                configuration=self.config.report_generation_config,
                language_model_service=self._language_model_service,
                notifier=self._notifier,
                memory_service=self._memory_service,
                knowledge_base_service=self._knowledge_base_service,
                cache_scope_id=self.config.cache_scope_id,
                content_chunk_registry=self._content_chunk_registry,
                citation_manager=self._citation_manager,
            )
            result = await executor.run(plan=plan, sources=sources)
            report = REPORT_TEMPLATE.render(**result.model_dump())

            references = self._citation_manager.get_references(
                message_id=self._event.payload.assistant_message.id
            )
            content_chunks = self._citation_manager.get_referenced_content_chunks()

            self._chat_service.modify_assistant_message(
                message_id=self._event.payload.assistant_message.id,
                content=report,
                references=references,
            )
        except Exception as e:
            self._notifier.end_progress(success=False)
            _LOGGER.exception(f"Error running SWOT plan: {e}")
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                content=f"Error running SWOT plan: {e}",
                content_chunks=[],
            )

        self._notifier.end_progress(success=True)

        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=self.name,
            content=report,
            content_chunks=content_chunks,
        )

    @override
    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []

    @override
    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    @override
    def get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
        agent_chunks_handler: AgentChunksHandler,
    ) -> LanguageModelMessage:
        return LanguageModelMessage(
            role=LanguageModelMessageRole.TOOL,
            content=tool_response.content,
        )

    @override
    def takes_control(self) -> bool:  # type: ignore
        """
        Some tools require to take control of the conversation with the user and do not want the orchestrator to intervene.
        this function indicates whether the tool takes control or not. It yanks the control away from the orchestrator.
        A typical use-case is deep-research.
        """
        return True

    def _calculate_total_steps(self, plan: SWOTPlan, number_of_sources: int) -> int:
        number_of_executions = plan.get_number_of_executions()
        num_steps_per_execution = number_of_sources + 1  # +1 for the summarization step

        return number_of_executions * num_steps_per_execution


ToolFactory.register_tool(tool=SwotAnalysisTool, tool_config=SwotAnalysisToolConfig)
