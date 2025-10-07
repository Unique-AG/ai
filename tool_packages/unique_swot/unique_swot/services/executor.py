"""
SWOT Analysis Execution Manager

This module provides the main execution manager logic for executing SWOT analysis plans.
The execution manager coordinates between different services including memory management,
report generation, and progress notification to execute complete SWOT analysis workflows.
"""

from logging import getLogger

from unique_toolkit import ShortTermMemoryService
from unique_toolkit.language_model import LanguageModelService

from unique_swot.services.generation import (
    ReportGenerationConfig,
    ReportGenerationContext,
    ReportModifyContext,
    SWOTAnalysisModels,
    SWOTComponent,
    batch_parser,
    generate_report,
    get_analysis_model,
    get_generation_system_prompt,
    modify_report,
)
from unique_swot.services.memory import SwotMemoryService
from unique_swot.services.notifier import Notifier
from unique_swot.services.schemas import (
    ExecutedSWOTPlan,
    ExecutedSwotStep,
    Source,
    SWOTPlan,
)

logger = getLogger(__name__)


class SWOTExecutionManager:
    """
    Main execution manager for executing SWOT analysis plans.

    This class coordinates the execution of SWOT analysis workflows by managing
    the interaction between different services including memory, language models,
    and progress notification. It handles both generation and modification operations
    for SWOT analysis components.

    The execution manager maintains state through memory services and provides progress
    updates through the notification system.
    """

    def __init__(
        self,
        *,
        configuration: ReportGenerationConfig,
        language_model_service: LanguageModelService,
        short_term_memory_service: ShortTermMemoryService,
        notifier: Notifier,
    ):
        """
        Initialize the SWOT orchestrator with required services.

        Args:
            configuration: Settings for report generation (batching, model, etc.)
            language_model_service: Service for interacting with language models
            short_term_memory_service: Service for managing analysis state
            notifier: Service for sending progress notifications
        """
        self.configuration = configuration
        self.language_model_service = language_model_service
        self.notifier = notifier
        self.memory_service = SwotMemoryService(short_term_memory_service)

    async def run(self, *, plan: SWOTPlan, sources: list[Source]) -> ExecutedSWOTPlan:
        """
        Execute a complete SWOT analysis plan.

        This method processes each step in the SWOT plan, executing either generation
        or modification operations as specified. It maintains the execution state and
        builds a comprehensive result containing all completed steps and their results.

        Args:
            plan: The SWOT analysis plan containing steps to execute
            sources: List of data sources to analyze

        Returns:
            ExecutedSWOTPlan containing all completed steps and their results

        Raises:
            ValueError: If an invalid operation is encountered in the plan
        """
        executed_plan = ExecutedSWOTPlan(
            objective=plan.objective,
            steps=[],
        )
        for step in plan.steps:
            match step.operation:
                case "generate":
                    analysis = await self.run_generation_function(
                        component=step.component,
                        sources=sources,
                    )
                    executed_plan.steps.append(
                        ExecutedSwotStep.from_step_and_result(
                            step=step,
                            result=analysis,
                        )
                    )
                case "modify":
                    analysis = await self.run_modify_function(
                        component=step.component,
                        sources=sources,
                        modify_instruction=step.modify_instruction,
                    )
                    executed_plan.steps.append(
                        ExecutedSwotStep.from_step_and_result(
                            step=step,
                            result=analysis,
                        )
                    )
                case "retrieve":
                    analysis = await self.get_analysis(
                        component=step.component,
                        sources=sources,
                    )
                    executed_plan.steps.append(
                        ExecutedSwotStep.from_step_and_result(
                            step=step,
                            result=analysis,
                        )
                    )
                case _:
                    raise ValueError(f"Invalid operation: {step.operation}")

        return executed_plan

    async def run_modify_function(
        self,
        *,
        component: SWOTComponent,
        sources: list[Source],
        modify_instruction: str | None,
    ) -> SWOTAnalysisModels:
        """
        Execute a modify operation for a SWOT analysis component.

        This method attempts to modify an existing SWOT analysis based on new sources
        or specific instructions. It first checks memory for existing analysis, and if
        found, attempts to modify it. If no existing analysis is found or modification
        fails, it falls back to generating a new analysis.

        Note: The modify functionality is currently not fully implemented and will
        fall back to generation in all cases.

        Args:
            component: The SWOT component to modify (Strengths, Weaknesses, etc.)
            sources: List of new data sources to incorporate
            modify_instruction: Specific instruction for how to modify the analysis

        Returns:
            The modified or newly generated SWOT analysis
        """
        saved_analysis = self.memory_service.get(get_analysis_model(component))

        if not saved_analysis:
            logger.warning(
                "No SWOT analysis found in memory for component: %s. Falling back to generation",
                component,
            )
            return await self.run_generation_function(
                component=component,
                sources=sources,
            )

        logger.warning(
            "Modify function not implemented, Falling back to generation for component: %s",
            component,
        )

        return await self.run_generation_function(
            component=component,
            sources=sources,
        )

        # This should never happen as we include validation of the schema in the LLM call
        # to request the modify instruction if modify operation is requested
        assert modify_instruction is not None, "Modify instruction is required"

        context = ReportModifyContext(
            step_name=component,
            sources=sources,
            system_prompt=get_generation_system_prompt(component),
            modify_instruction=modify_instruction,
            structured_report=saved_analysis,
        )
        result = await modify_report(
            context=context,
            configuration=self.configuration,
            language_model_service=self.language_model_service,
            notifier=self.notifier,
        )

        self.memory_service.set(result)

        return result

    async def run_generation_function(
        self, *, component: SWOTComponent, sources: list[Source]
    ) -> SWOTAnalysisModels:
        """
        Execute a generation operation for a SWOT analysis component.

        This method generates a new SWOT analysis for the specified component using
        the provided sources. It creates the appropriate context, calls the report
        generation service, and stores the result in memory for potential future
        modifications.

        Args:
            component: The SWOT component to generate (Strengths, Weaknesses, etc.)
            sources: List of data sources to analyze

        Returns:
            The generated SWOT analysis for the specified component
        """
        context = ReportGenerationContext(
            step_name=component,
            sources=sources,
            system_prompt=get_generation_system_prompt(component),
            output_model=get_analysis_model(component),
        )
        result = await generate_report(
            context=context,
            configuration=self.configuration,
            language_model_service=self.language_model_service,
            notifier=self.notifier,
            batch_parser=batch_parser,
        )

        self.memory_service.set(result)

        return result

    async def get_analysis(
        self, component: SWOTComponent, sources: list[Source]
    ) -> SWOTAnalysisModels:
        saved_analysis = self.memory_service.get(get_analysis_model(component))

        # If we have a saved analysis, return it
        if saved_analysis:
            return saved_analysis

        # If we don't have a saved analysis, generate a new one
        logger.warning(
            "No SWOT analysis found in memory for component: %s. Falling back to generation",
            component,
        )
        return await self.run_generation_function(
            component=component,
            sources=sources,
        )
