from datetime import datetime, timedelta
from logging import getLogger

from typing_extensions import override
from unique_quartr.service import QuartrService
from unique_toolkit import ShortTermMemoryService
from unique_toolkit._common.docx_generator import DocxGeneratorService
from unique_toolkit._common.endpoint_requestor import RequestorType
from unique_toolkit.agentic.tools.agent_chunks_hanlder import AgentChunksHandler
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import (
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
from unique_swot.services.report import ReportDeliveryService
from unique_swot.services.schemas import SWOTPlan
from unique_swot.services.session.schema import SessionConfig

_LOGGER = getLogger(__name__)


class SwotAnalysisTool(Tool[SwotAnalysisToolConfig]):
    name = "SwotAnalysis"

    def __init__(self, configuration: SwotAnalysisToolConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)

        self._swot_analysis_session_config = SessionConfig.model_validate(
            self._event.payload.session_config, by_name=True
        )

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

        self._earnings_call_docx_generator_service = DocxGeneratorService(
            chat_service=self._chat_service,
            knowledge_base_service=self._knowledge_base_service,
            config=self.config.earnings_call_config.docx_renderer_config,
        )

        self._report_docx_renderer = DocxGeneratorService(
            chat_service=self._chat_service,
            knowledge_base_service=self._knowledge_base_service,
            config=self.config.report_renderer_config.docx_renderer_config,
        )

        self._source_collection_manager = SourceCollectionManager(
            context=CollectionContext(
                use_earnings_calls=self._swot_analysis_session_config.swot_analysis.use_earnings_call,
                use_web_sources=self._swot_analysis_session_config.swot_analysis.use_web_sources,
                metadata_filter=metadata_filter,
                company=self._swot_analysis_session_config.swot_analysis.company_listing,
                earnings_call_start_date=self._swot_analysis_session_config.swot_analysis.earnings_call_start_date
                or datetime.now() - timedelta(days=365),
                upload_scope_id_earnings_calls=self.config.earnings_call_config.upload_scope_id,
            ),
            knowledge_base_service=self._knowledge_base_service,
            content_chunk_registry=self._content_chunk_registry,
            notifier=self._notifier,
            quartr_service=self._get_quartr_service(self._event.company_id),
            earnings_call_docx_generator_service=self._earnings_call_docx_generator_service,
        )

        self._citation_manager = CitationManager(
            content_chunk_registry=self._content_chunk_registry,
        )

        self._report_delivery_service = ReportDeliveryService(
            chat_service=self._chat_service,
            template_name=self.config.report_renderer_config.report_template,
            docx_renderer=self._report_docx_renderer,
            citation_manager=self._citation_manager,
            renderer_type=self.config.report_renderer_config.renderer_type,
            message_id=self._event.payload.assistant_message.id,
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
        company_name = (
            self._swot_analysis_session_config.swot_analysis.company_listing.name
        )
        try:
            plan = SWOTPlan.model_validate(tool_call.arguments)
            # Ensure the plan is semantically valid for execution, as Pydantic validation may accept plans that
            # are structurally correct but logically invalid (e.g., missing required modify instructions)

            plan.validate_swot_plan()

            number_of_executions = (
                plan.get_number_of_executions() + 1
            )  # +1 for Collecting sources step

            self._notifier.start_progress(
                number_of_executions,
                company_name,
            )

            # Get Sources
            sources = await self._source_collection_manager.collect_sources()

            _LOGGER.info(f"Collected {len(sources)} sources!")

            total_steps = self._calculate_total_steps(plan, len(sources))
            _LOGGER.info(f"Total steps: {total_steps}")
            executor = SWOTExecutionManager(
                company_name=company_name,
                configuration=self.config.report_generation_config,
                language_model_service=self._language_model_service,
                notifier=self._notifier,
                memory_service=self._memory_service,
                knowledge_base_service=self._knowledge_base_service,
                content_chunk_registry=self._content_chunk_registry,
                citation_manager=self._citation_manager,
            )
            # Generate markdown report
            result = await executor.run(plan=plan, sources=sources)

            # Store the result in memory
            self._memory_service.set(result)

            self._notifier.end_progress(failed=False)

            # Deliver the report to the chat
            markdown_report = self._report_delivery_service.deliver_report(
                company_name=company_name,
                result=result,
                docx_template_fields={
                    "title": f"{company_name} SWOT Analysis Report",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                },
            )

            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                content=markdown_report,
                content_chunks=self._citation_manager.get_referenced_content_chunks(),
            )

        except Exception as e:
            self._notifier.end_progress(failed=True, failure_message=str(e))
            _LOGGER.exception(f"Error running SWOT plan: {e}")
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                content=f"Error running SWOT plan: {e}",
                content_chunks=[],
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
    def get_tool_call_result_for_loop_history(  # type: ignore
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

    @staticmethod
    def _get_quartr_service(company_id: str) -> QuartrService | None:
        try:
            return QuartrService(
                company_id=company_id,
                requestor_type=RequestorType.REQUESTS,
            )
        except Exception as e:
            _LOGGER.error(f"Error getting Quartr service: {e}")
            return None


ToolFactory.register_tool(tool=SwotAnalysisTool, tool_config=SwotAnalysisToolConfig)
