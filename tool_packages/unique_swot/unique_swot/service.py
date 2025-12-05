from datetime import datetime, timedelta
from logging import getLogger

from typing_extensions import override
from unique_quartr.service import QuartrService
from unique_toolkit import ShortTermMemoryService
from unique_toolkit._common.docx_generator import DocxGeneratorService
from unique_toolkit._common.experimental.endpoint_requestor import RequestorType
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
from unique_swot.services.generation.extraction.agent import ExtractorAgent
from unique_swot.services.generation.reporting.agent import ProgressiveReportingAgent
from unique_swot.services.memory.base import SwotMemoryService
from unique_swot.services.notification.notifier import Notifier
from unique_swot.services.orchestrator.service import SWOTOrchestrator
from unique_swot.services.report import ReportDeliveryService, ReportRendererConfig
from unique_swot.services.schemas import SWOTPlan
from unique_swot.services.session import SessionConfig
from unique_swot.services.source_management.collection.base import (
    CollectionContext,
    SourceCollectionManager,
)
from unique_swot.services.source_management.iteration.date_relevancy import (
    DateRelevancySourceIterator,
)
from unique_swot.services.source_management.registry import ContentChunkRegistry
from unique_swot.services.source_management.selection.agent import SourceSelectionAgent

_LOGGER = getLogger(__name__)


class SwotAnalysisTool(Tool[SwotAnalysisToolConfig]):
    name = "SwotAnalysis"

    def __init__(self, configuration: SwotAnalysisToolConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)

        self._metadata_filter = self._event.payload.metadata_filter

        self._knowledge_base_service = KnowledgeBaseService.from_event(self._event)

        self._short_term_memory_service = ShortTermMemoryService(
            company_id=self._event.company_id,
            user_id=self._event.user_id,
            chat_id=self._event.payload.chat_id,
            message_id=None,
        )

    def _get_document_template(self, template_content_id: str | None) -> bytes | None:
        if not template_content_id:
            return None
        try:
            file_content = self._knowledge_base_service.download_content_to_bytes(
                content_id=template_content_id
            )
        except Exception as e:
            _LOGGER.warning(
                f"An error occurred while downloading the template {e}. Make sure the template content ID is valid. Falling back to default template."
            )
            return None
        return file_content

    def _try_load_session_config(self):
        try:
            return SessionConfig.model_validate(
                self._event.payload.session_config, by_name=True
            )
        except Exception as e:
            _LOGGER.error(f"Error validating session config: {e}")
            return None

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
        session_config = self._try_load_session_config()
        if not session_config:
            self._chat_service.modify_assistant_message(
                content="Please make sure to provide the mandatory fields in the SWOT Analysis side bar configuration."
            )
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                content="The user has not provided a valid configuration for the SWOT. He must provide a valid configuration before running the tool.",
                content_chunks=[],
            )
        company_name = session_config.swot_analysis.company_listing.name
        # This service is responsible for notifying the user of the progress of the SWOT analysis
        notifier = self._get_notifier()

        await notifier.init_progress(
            session_info=session_config.swot_analysis.render_session_info()
        )

        try:
            plan = SWOTPlan.model_validate(tool_call.arguments)
            # Ensure the plan is semantically valid for execution, as Pydantic validation may accept plans that
            # are structurally correct but logically invalid (e.g., missing required modify instructions)

            plan.validate_swot_plan()

            # This service is used to store intermediate results of the SWOT analysis
            memory_service = SwotMemoryService(
                short_term_memory_service=self._short_term_memory_service,
                knowledge_base_service=self._knowledge_base_service,
                cache_scope_id=self.config.cache_scope_id,
            )

            # This service is used to store the content chunks and generate unique IDs for them
            # It is used to track the content chunks and generate citations for the report
            content_chunk_registry = self._get_content_chunk_registry(
                memory_service=memory_service
            )

            # This service is used to collect the sources from the knowledge base
            # It is used to collect the sources from the knowledge base
            source_collector = self._get_source_collector(
                chunk_registry=content_chunk_registry,
                knowledge_base_service=self._knowledge_base_service,
                session_config=session_config,
                notifier=notifier,
            )

            # This service is used to define what sources are relevant for the SWOT analysis and what are not
            source_selector = self._get_source_selector()

            # This service is used to define the order in which the sources are processed
            source_iterator = self._get_source_iterator()

            # This service is used to extract the relevant information from the sources
            extractor = self._get_extractor()

            # This service is used to generate the report from the extracted information
            report_manager = self._get_report_manager(
                memory_service=memory_service,
            )

            # This service is used to orchestrate the SWOT analysis
            orchestrator = SWOTOrchestrator(
                notifier=notifier,
                source_collector=source_collector,
                source_iterator=source_iterator,
                source_selector=source_selector,
                extractor=extractor,
                report_manager=report_manager,
                memory_service=memory_service,
            )

            # Generate markdown report
            result = await orchestrator.run(company_name=company_name, plan=plan)

            await notifier.end_progress(failed=False)

            citation_manager = self._get_citation_manager(content_chunk_registry)

            report_delivery_service = self._get_report_delivery_service(
                citation_manager=citation_manager,
                report_renderer_config=self.config.report_renderer_config,
            )

            # Deliver the report to the chat
            markdown_report = report_delivery_service.deliver_report(
                session_config=session_config.swot_analysis,
                result=result,
                docx_template_fields={
                    "title": f"{company_name} SWOT Analysis Report",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                },
                ingest_docx=self.config.report_renderer_config.ingest_docx_report,
            )

            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                content=markdown_report,
                content_chunks=citation_manager.get_referenced_content_chunks(),
            )

        except Exception as e:
            await notifier.end_progress(failed=True, failure_message=str(e))
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

    def _get_source_collector(
        self,
        chunk_registry: ContentChunkRegistry,
        knowledge_base_service: KnowledgeBaseService,
        session_config: SessionConfig,
        notifier: Notifier,
    ) -> SourceCollectionManager:
        earnings_call_docx_generator_service = DocxGeneratorService(
            config=self.config.source_management_config.earnings_call_config.docx_renderer_config,
            template=self._get_document_template(
                self.config.source_management_config.earnings_call_config.docx_renderer_config.template_content_id
            ),
        )

        collection_context = CollectionContext(
            use_earnings_calls=session_config.swot_analysis.use_earnings_call,
            use_web_sources=session_config.swot_analysis.use_web_sources,
            metadata_filter=self._metadata_filter,
            company=session_config.swot_analysis.company_listing,
            earnings_call_start_date=session_config.swot_analysis.earnings_call_start_date
            or datetime.now() - timedelta(days=365),
            upload_scope_id_earnings_calls=self.config.source_management_config.earnings_call_config.upload_scope_id,
        )

        return SourceCollectionManager(
            context=collection_context,
            knowledge_base_service=knowledge_base_service,
            content_chunk_registry=chunk_registry,
            notifier=notifier,
            quartr_service=self._get_quartr_service(self._event.company_id),
            earnings_call_docx_generator_service=earnings_call_docx_generator_service,
        )

    def _get_source_selector(self) -> SourceSelectionAgent:
        return SourceSelectionAgent(
            llm_service=self._language_model_service,
            llm=self.config.language_model,
            source_selection_config=self.config.source_management_config.source_selection_config,
        )

    def _get_source_iterator(self) -> DateRelevancySourceIterator:
        return DateRelevancySourceIterator(
            config=self.config.source_management_config.date_relevancy_config,
        )

    def _get_extractor(self) -> ExtractorAgent:
        return ExtractorAgent(
            llm_service=self._language_model_service,
            llm=self.config.language_model,
            extraction_config=self.config.extraction_config,
        )

    def _get_report_manager(
        self, memory_service: SwotMemoryService
    ) -> ProgressiveReportingAgent:
        return ProgressiveReportingAgent(
            memory_service=memory_service,
            llm_service=self._language_model_service,
            llm=self.config.report_generation_config.language_model,
            reporting_config=self.config.report_generation_config.reporting_config,
        )

    def _get_content_chunk_registry(
        self, memory_service: SwotMemoryService
    ) -> ContentChunkRegistry:
        content_chunk_registry = ContentChunkRegistry(memory_service=memory_service)
        return content_chunk_registry

    def _get_citation_manager(
        self, content_chunk_registry: ContentChunkRegistry
    ) -> CitationManager:
        citation_manager = CitationManager(
            content_chunk_registry=content_chunk_registry
        )
        return citation_manager

    def _get_report_delivery_service(
        self,
        citation_manager: CitationManager,
        report_renderer_config: ReportRendererConfig,
    ) -> ReportDeliveryService:
        report_docx_renderer = DocxGeneratorService(
            config=report_renderer_config.docx_renderer_config,
            template=self._get_document_template(
                report_renderer_config.docx_renderer_config.template_content_id
            ),
        )
        return ReportDeliveryService(
            chat_service=self._chat_service,
            docx_renderer=report_docx_renderer,
            citation_manager=citation_manager,
            renderer_type=report_renderer_config.renderer_type,
            template_name=report_renderer_config.report_template,
        )

    def _get_notifier(self) -> Notifier:
        return Notifier(
            chat_service=self._chat_service,
            message_id=self._event.payload.assistant_message.id,
        )


ToolFactory.register_tool(tool=SwotAnalysisTool, tool_config=SwotAnalysisToolConfig)
