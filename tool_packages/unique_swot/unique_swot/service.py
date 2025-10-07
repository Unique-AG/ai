from typing_extensions import override
from unique_toolkit import ShortTermMemoryService
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import EvaluationMetricName, Tool
from unique_toolkit.knowledge_base import KnowledgeBaseService
from unique_toolkit.language_model import LanguageModelFunction
from unique_toolkit.language_model.schemas import LanguageModelToolDescription

from unique_swot.config import SwotConfig
from unique_swot.services.collection import CollectionContext, SourceCollectionManager
from unique_swot.services.executor import SWOTExecutionManager
from unique_swot.services.notifier import LoggerNotifier
from unique_swot.services.schemas import SWOTPlan


class SwotTool(Tool[SwotConfig]):
    name = "Swot"

    def __init__(self, configuration: SwotConfig, *args, **kwargs):
        super().__init__(configuration, *args, **kwargs)

        context = CollectionContext.from_event(self._event)
        knowledge_base_service = KnowledgeBaseService.from_event(self._event)
        self.source_collection_manager = SourceCollectionManager(
            context=context,
            knowledge_base_service=knowledge_base_service,
            where_clause={},
        )
        self._notifier = LoggerNotifier()
        self._short_term_memory_service = ShortTermMemoryService.from_event(self._event)

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
        plan.validate_swot_plan()
        

        sources = self.source_collection_manager.collect_sources()
        
        # TODO: Estimate number of steps based on the plan and the number of sources
        
        executor = SWOTExecutionManager(
            configuration=self.config.report_generation_config,
            language_model_service=self._language_model_service,
            notifier=self._notifier,
            short_term_memory_service=self._short_term_memory_service,
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


ToolFactory.register_tool(tool=SwotTool, tool_config=SwotConfig)
