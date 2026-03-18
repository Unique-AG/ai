"""Web Search V3 executor: snippet judge (score + rank) before crawling."""

import logging
from time import time

from unique_toolkit.language_model import LanguageModelFunction

from unique_web_search.schema import Step, StepDebugInfo, WebSearchPlan
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.executors.web_search_v2_executor import (
    WebSearchV2Executor,
)
from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.snippet_judge import (
    SnippetJudgeConfig,
    select_relevant,
)

_LOGGER = logging.getLogger(__name__)


class WebSearchV3Executor(WebSearchV2Executor):
    """Executes research plans with snippet-based relevance filtering before crawling.

    For each search step: fetch results -> LLM judge (score + explain, then rank) ->
    crawl only top-ranked URLs -> content processing -> select relevant sources.
    """

    def __init__(
        self,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        tool_parameters: WebSearchPlan,
        max_steps: int = 3,
        snippet_judge_config: SnippetJudgeConfig | None = None,
    ):
        super().__init__(
            services=services,
            config=config,
            callbacks=callbacks,
            tool_call=tool_call,
            tool_parameters=tool_parameters,
            max_steps=max_steps,
        )
        self.snippet_judge_config = snippet_judge_config or SnippetJudgeConfig()
        _LOGGER.info(
            f"Snippet judge config: {self.snippet_judge_config.model_dump_json()}"
        )

    async def _after_search_before_crawl(
        self, step: Step, results: list[WebSearchResult]
    ) -> list[WebSearchResult]:
        """Run snippet judge to narrow results before crawling."""
        if not results or not self.search_service.requires_scraping:
            return results

        step_name = step.step_type.name
        objective = step.objective or self.tool_parameters.objective
        number_before_judge = len(results)
        time_judge_start = time()
        _LOGGER.info(
            f"Company {self.company_id} Running snippet judge to narrow results"
        )
        try:
            selected = await select_relevant(
                objective=objective,
                results=results,
                language_model_service=self.language_model_service,
                language_model=self.language_model,
                config=self.snippet_judge_config,
            )
            _LOGGER.info(
                f"Company {self.company_id} Snippet judge selected {len(selected)} results from {number_before_judge}"
            )

            results = selected
        except Exception as e:
            _LOGGER.warning("Snippet judge failed, using all search results: %s", e)
            results = results[: self.snippet_judge_config.max_urls_to_select]

        judge_time = time() - time_judge_start
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name=f"{step_name}.snippet_judge",
                execution_time=judge_time,
                config="snippet_judge",
                extra={
                    "number_of_results_before": number_before_judge,
                    "number_of_results_after": len(results),
                },
            )
        )
        return results
