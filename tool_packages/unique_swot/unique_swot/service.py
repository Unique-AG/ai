from typing_extensions import override
from unique_toolkit import ShortTermMemoryService
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import (
    AgentChunksHandler,
    EvaluationMetricName,
    Tool,
)

# from unique_toolkit.chat.schemas import (
#     MessageExecutionType,
#     MessageLogDetails,
#     MessageLogEvent,
#     MessageLogStatus,
#     MessageLogUncitedReferences,
# )
from unique_toolkit.language_model import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelMessageRole,
)
from unique_toolkit.language_model.schemas import LanguageModelToolDescription
from unique_toolkit.services.knowledge_base import KnowledgeBaseService

from unique_swot.config import SwotConfig
from unique_swot.services.collection import CollectionContext, SourceCollectionManager
from unique_swot.services.collection.registry import ContentChunkRegistry
from unique_swot.services.executor import SWOTExecutionManager
from unique_swot.services.memory.base import SwotMemoryService
from unique_swot.services.notifier import LoggerNotifier
from unique_swot.services.schemas import SWOTPlan

mock_metadata_filter = {
    "and": [
        {
            "or": [
                {
                    "operator": "contains",
                    "path": ["folderIdPath"],
                    "value": "scope_xfmvf7vx68xj1y33e1gfmz9b",
                }
            ]
        }
    ]
}

mock_metadata_filter = {
    "and": [
        {
            "or": [
                {
                    "operator": "in",
                    "path": ["contentId"],
                    "value": ["cont_fzj2je28tj5eexqxjz2s1pqf"],
                }
            ]
        }
    ]
}


class SwotTool(Tool[SwotConfig]):
    name = "SWOT"

    def __init__(self, configuration: SwotConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)

        self._knowledge_base_service = KnowledgeBaseService.from_event(self._event)

        self._notifier = LoggerNotifier()

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

        self.source_collection_manager = SourceCollectionManager(
            context=CollectionContext(
                use_earnings_calls=False,
                use_web_sources=False,
                metadata_filter=mock_metadata_filter,
            ),
            knowledge_base_service=self._knowledge_base_service,
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
        plan = SWOTPlan.model_validate(tool_call.arguments)
        # Ensure the plan is semantically valid for execution, as Pydantic validation may accept plans that
        # are structurally correct but logically invalid (e.g., missing required modify instructions)
        # self._chat_service.create_message_log(
        #     message_id=self._event.payload.assistant_message.id,
        #     text="Running SWOT plan",
        #     status=MessageLogStatus.RUNNING,
        #     order=0,
        #     details=MessageLogDetails(
        #         data=[MessageLogEvent(type="SWOTAnalysis", text=plan.objective)]
        #     ),
        #     uncited_references=MessageLogUncitedReferences(data=[]),
        # )
        # self._chat_service.create_message_execution(
        #     message_id=self._event.payload.assistant_message.id,
        #     type=MessageExecutionType.DEEP_RESEARCH,
        #     seconds_remaining=60 * 60 * 24, # 24 hours
        #     percentage_completed=50,
        # )
        # await sleep(10)
        plan.validate_swot_plan()

        self.logger.info(f"Running SWOT plan: {plan.model_dump_json(indent=2)}")

        # Get Sources
        sources = self.source_collection_manager.collect_sources()

        # Save Registry

        self.logger.info(f"Collected {len(sources)} sources!")

        # TODO: Estimate number of steps based on the plan and the number of sources

        executor = SWOTExecutionManager(
            configuration=self.config.report_generation_config,
            language_model_service=self._language_model_service,
            notifier=self._notifier,
            memory_service=self._memory_service,
            knowledge_base_service=self._knowledge_base_service,
            cache_scope_id=self.config.cache_scope_id,
        )
        result = await executor.run(plan=plan, sources=sources)

        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=self.name,
            content=result.model_dump_json(indent=2),
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


ToolFactory.register_tool(tool=SwotTool, tool_config=SwotConfig)
