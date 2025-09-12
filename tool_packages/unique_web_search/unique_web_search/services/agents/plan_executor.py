import logging
from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel, Field
from unique_toolkit import LanguageModelService
from unique_toolkit.language_model import LanguageModelFunction, LanguageModelName
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)

from unique_web_search.services.agents.plan_agent import (
    ResearchPlan,
    SearchStep,
    StepType,
    step_type_to_name,
)
from unique_web_search.services.crawlers import CrawlerTypes
from unique_web_search.services.search_and_crawl import SearchAndCrawlService
from unique_web_search.services.search_engine import SearchEngineTypes, WebSearchResult

logger = logging.getLogger(f"PythonAssistantCoreBundle.{__name__}")


class ExecutionStatus(StrEnum):
    """Status of step execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepResult(BaseModel):
    """Result of executing a single step."""

    step_index: int
    step_type: StepType
    objective: str
    status: ExecutionStatus
    search_results: Optional[List[WebSearchResult]] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExecutionResult(BaseModel):
    """Complete execution result for a research plan."""

    plan: ResearchPlan
    step_results: List[StepResult]
    total_execution_time: float
    successful_steps: int
    failed_steps: int
    final_content: List[WebSearchResult] = Field(default_factory=list)
    synthesis_result: Optional[List[WebSearchResult]] = None
    execution_summary: str = ""


class WebSearchResults(BaseModel):
    """Result of performing web search."""

    results: List[WebSearchResult]


class PlanExecutor:
    """Executes research plans step by step."""

    def __init__(
        self,
        search_service: SearchEngineTypes,
        language_model_service: LanguageModelService,
        language_model: LanguageModelName,
        crawler_service: CrawlerTypes,
        tool_call: LanguageModelFunction,
        tool_progress_reporter: Optional[ToolProgressReporter] = None,
        encoder_name: str = "cl100k_base",
        percentage_of_input_tokens_for_sources: float = 0.7,
        token_limit_input: int = 100000,
    ):
        self.search_service = search_service
        self.crawler_service = crawler_service
        self.search_and_crawl_service = SearchAndCrawlService(
            search_engine_service=search_service,
            crawler_service=crawler_service,
        )
        self.language_model_service = language_model_service
        self.language_model = language_model
        self.tool_progress_reporter = tool_progress_reporter
        self.encoder_name = encoder_name
        self.percentage_of_input_tokens_for_sources = (
            percentage_of_input_tokens_for_sources
        )
        self.token_limit_input = token_limit_input

        async def notify_callback(step: SearchStep, state: ProgressState):
            if self.tool_progress_reporter:
                await self.tool_progress_reporter.notify_from_tool_call(
                    tool_call=tool_call,
                    name=step_type_to_name[step.step_type],
                    message=step.objective,
                    state=state,
                )
            else:
                logger.info(f"Searching: {step.query}")

        self.notify_callback = notify_callback

    async def execute_plan(self, plan: ResearchPlan) -> ExecutionResult:
        """Execute a complete research plan."""
        start_time = datetime.now()
        step_results: List[StepResult] = []
        all_content: List[WebSearchResult] = []

        # Initialize step results
        for i, step in enumerate(plan.steps):
            step_results.append(
                StepResult(
                    step_index=i,
                    step_type=step.step_type,
                    objective=step.objective,
                    status=ExecutionStatus.PENDING,
                )
            )

        # Execute steps in dependency order
        execution_order = self._resolve_execution_order(plan.steps)

        for step_index in execution_order:
            step = plan.steps[step_index]
            step_result = step_results[step_index]

            # Check if dependencies are satisfied
            if not self._dependencies_satisfied(step, step_results):
                step_result.status = ExecutionStatus.SKIPPED
                step_result.error_message = "Dependencies not satisfied"
                continue

            # Execute the step
            try:
                await self.notify_callback(step, ProgressState.RUNNING)
                await self._execute_step(step, step_result, all_content)
                if step_result.search_results:
                    all_content.extend(step_result.search_results)
            except Exception as e:
                await self.notify_callback(step, ProgressState.FAILED)
                logger.error(f"Failed to execute step {step_index}: {str(e)}")
                step_result.status = ExecutionStatus.FAILED
                step_result.error_message = str(e)

        await self.notify_callback(plan.steps[-1], ProgressState.FINISHED)

        # Perform synthesis if there are synthesize steps
        synthesis_result = await self._perform_synthesis(
            plan, step_results, all_content
        )

        # Calculate execution summary
        execution_time = (datetime.now() - start_time).total_seconds()
        successful_steps = sum(
            1 for r in step_results if r.status == ExecutionStatus.COMPLETED
        )
        failed_steps = sum(
            1 for r in step_results if r.status == ExecutionStatus.FAILED
        )

        return ExecutionResult(
            plan=plan,
            step_results=step_results,
            total_execution_time=execution_time,
            successful_steps=successful_steps,
            failed_steps=failed_steps,
            final_content=all_content,
            synthesis_result=synthesis_result,
            execution_summary=self._create_execution_summary(
                step_results, successful_steps, failed_steps
            ),
        )

    async def _execute_step(
        self,
        step: SearchStep,
        result: StepResult,
        context_content: List[WebSearchResult],
    ):
        """Execute a single step based on its type."""
        result.status = ExecutionStatus.RUNNING
        result.started_at = datetime.now()

        try:
            if step.step_type == StepType.SEARCH:
                await self._execute_search_step(step, result)
            elif step.step_type == StepType.READ_URL:
                await self._execute_read_url_step(step, result)
            elif step.step_type == StepType.VERIFY:
                await self._execute_verify_step(step, result, context_content)
            elif step.step_type == StepType.SYNTHESIZE:
                await self._execute_synthesize_step(step, result, context_content)
            elif step.step_type == StepType.FOLLOW_UP:
                await self._execute_follow_up_step(step, result, context_content)

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            raise
        finally:
            result.status = ExecutionStatus.COMPLETED
            result.completed_at = datetime.now()
            if result.started_at:
                result.execution_time = (
                    result.completed_at - result.started_at
                ).total_seconds()

    async def _execute_search_step(self, step: SearchStep, result: StepResult):
        """Execute a search step."""
        if not step.query:
            raise ValueError("Search step requires a query")
        # Prepare search parameters
        search_kwargs = {}
        if step.restrict_date:
            search_kwargs["restrict_date"] = step.restrict_date

        # Perform search and crawl
        search_results, metrics = await self.search_and_crawl_service.search_and_crawl(
            step.query, **search_kwargs
        )

        result.search_results = search_results

        logger.info(f"Search completed: {len(search_results)} results")

    async def _execute_read_url_step(self, step: SearchStep, result: StepResult):
        """Execute a read URL step."""
        if not step.urls:
            raise ValueError("Read URL step requires URLs")

        content_strings = await self.crawler_service.crawl(step.urls)

        search_results = []
        for url, content in zip(step.urls, content_strings):
            search_results.append(
                WebSearchResult(url=url, content=content, snippet="", title="")
            )
        result.search_results = search_results

        logger.info(f"URL reading completed: {len(search_results)} results")

    async def _execute_verify_step(
        self,
        step: SearchStep,
        result: StepResult,
        context_content: List[WebSearchResult],
    ):
        """Execute a verification step."""
        # Use LLM to verify information from context
        verification_prompt = f"""
        Verify the following information based on the provided sources:
        
        Objective: {step.objective}
        
        Please analyze the sources and provide:
        1. Verification status (verified/partially verified/not verified/conflicting)
        2. Supporting evidence
        3. Any conflicting information found
        4. Confidence level (high/medium/low)
        """

        # Combine context content for verification
        context_text = "\n\n".join(
            [chunk.content for chunk in context_content[-10:]]
        )  # Last 10 chunks

        messages = (
            MessagesBuilder()
            .system_message_append(
                "You are an expert fact-checker. Analyze the provided sources carefully."
            )
            .user_message_append(f"{verification_prompt}\n\nSources:\n{context_text}")
            .build()
        )

        response = await self.language_model_service.complete_async(
            messages,
            model_name=self.language_model.name,
            structured_output_model=WebSearchResults,
        )

        verification_result = WebSearchResults.model_validate(
            response.choices[0].message.parsed
        )

        # Create a content chunk with verification results
        result.search_results = verification_result.results

        logger.info("Verification completed")

    async def _execute_synthesize_step(
        self,
        step: SearchStep,
        result: StepResult,
        context_content: List[WebSearchResult],
    ):
        """Execute a synthesis step."""

        synthesis_prompt = f"""
        Synthesize the following information to answer the objective:
        
        Objective: {step.objective}
        
        Please provide:
        1. A comprehensive summary
        2. Key findings
        3. Any gaps in information
        4. Conclusions and insights
        """

        # Use recent context content for synthesis
        context_text = "\n\n".join([chunk.content for chunk in context_content])

        messages = (
            MessagesBuilder()
            .system_message_append(
                "You are an expert researcher. Synthesize information comprehensively."
            )
            .user_message_append(
                f"{synthesis_prompt}\n\nInformation to synthesize:\n{context_text}"
            )
            .build()
        )

        response = await self.language_model_service.complete_async(
            messages,
            model_name=self.language_model.name,
            structured_output_model=WebSearchResults,
        )

        synthesis_result = WebSearchResults.model_validate(
            response.choices[0].message.parsed
        )

        result.search_results = synthesis_result.results

        logger.info("Synthesis completed")

    async def _execute_follow_up_step(
        self,
        step: SearchStep,
        result: StepResult,
        context_content: List[WebSearchResult],
    ):
        """Execute a follow-up search step based on context."""
        if not step.query:
            raise ValueError("Follow-up step requires a query")

        # This is similar to search but might use context to refine the query
        await self._execute_search_step(step, result)

        logger.info("Follow-up search completed")

    def _resolve_execution_order(self, steps: List[SearchStep]) -> List[int]:
        """Resolve the execution order based on dependencies."""
        order = []
        remaining = set(range(len(steps)))

        while remaining:
            # Find steps with no unresolved dependencies
            ready = []
            for i in remaining:
                step = steps[i]
                if not step.depends_on or all(dep in order for dep in step.depends_on):
                    ready.append(i)

            if not ready:
                # Circular dependency or invalid dependency, add remaining in order
                ready = list(remaining)

            # Sort by priority (lower number = higher priority)
            ready.sort(key=lambda i: steps[i].priority)

            for step_index in ready:
                order.append(step_index)
                remaining.remove(step_index)

        return order

    def _dependencies_satisfied(
        self, step: SearchStep, step_results: List[StepResult]
    ) -> bool:
        """Check if step dependencies are satisfied."""
        if not step.depends_on:
            return True

        for dep_index in step.depends_on:
            if dep_index >= len(step_results):
                return False
            if step_results[dep_index].status != ExecutionStatus.COMPLETED:
                return False

        return True

    async def _perform_synthesis(
        self,
        plan: ResearchPlan,
        step_results: List[StepResult],
        all_content: List[WebSearchResult],
    ) -> Optional[List[WebSearchResult]]:
        """Perform final synthesis of all gathered information."""
        if not all_content:
            return None

        synthesis_prompt = f"""
        Based on the research plan and gathered information, provide a comprehensive answer:
        
        Original Query: {plan.query_analysis}
        Expected Outcome: {plan.expected_outcome}
        
        Please synthesize all the information to provide a complete, accurate, and well-structured response.
        """

        # Combine all content
        context_text = "\n\n".join([chunk.content for chunk in all_content])

        messages = (
            MessagesBuilder()
            .system_message_append(
                "You are an expert researcher providing final synthesis."
            )
            .user_message_append(
                f"{synthesis_prompt}\n\nGathered Information:\n{context_text}"
            )
            .build()
        )

        response = await self.language_model_service.complete_async(
            messages,
            model_name=self.language_model.name,
            structured_output_model=WebSearchResults,
        )

        return WebSearchResults.model_validate(
            response.choices[0].message.parsed
        ).results

    def _create_execution_summary(
        self, step_results: List[StepResult], successful_steps: int, failed_steps: int
    ) -> str:
        """Create a summary of the execution."""
        total_steps = len(step_results)

        summary = (
            f"Execution completed: {successful_steps}/{total_steps} steps successful"
        )

        if failed_steps > 0:
            failed_objectives = [
                r.objective for r in step_results if r.status == ExecutionStatus.FAILED
            ]
            summary += f", {failed_steps} failed: {', '.join(failed_objectives[:3])}"
            if len(failed_objectives) > 3:
                summary += f" and {len(failed_objectives) - 3} more"

        return summary
