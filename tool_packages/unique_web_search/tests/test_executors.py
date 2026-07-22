"""Tests for WebSearchV1Executor, WebSearchV2Executor, and WebSearchV3Executor."""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from unique_web_search.services.crawlers.url_safety import (
    CrawlTargetValidationError,
    UrlSafetyService,
)
from unique_web_search.services.executors.v1.config import RefineQueryMode
from unique_web_search.services.executors.v1.executor import (
    RefinedQueries,
    RefinedQuery,
    WebSearchV1Executor,
    query_generation_agent,
)
from unique_web_search.services.executors.v1.schema import WebSearchToolParameters
from unique_web_search.services.executors.v2.executor import (
    WebSearchV2Executor,
)
from unique_web_search.services.executors.v2.schema import Step, StepType, WebSearchPlan
from unique_web_search.services.executors.v3.executor import (
    WebSearchV3Executor,
)
from unique_web_search.services.executors.v3.schema import (
    Command,
    FetchUrlsPayload,
    SearchPayload,
    WebSearchV3ToolParameters,
)
from unique_web_search.services.search_engine.schema import WebSearchResult


class TestQueryGenerationAgent:
    """Tests for the query_generation_agent function."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_query_generation_agent__returns_unchanged_query__when_mode_is_deactivated(
        self, mocker: Any
    ) -> None:
        """
        Purpose: Verify query_generation_agent returns the original query when mode is DEACTIVATED.
        Why this matters: DEACTIVATED mode should not modify the query.
        Setup summary: Call with DEACTIVATED mode.
        """
        query = "test query"
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"

        result = await query_generation_agent(
            query=query,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            system_prompt="test prompt",
            mode=RefineQueryMode.DEACTIVATED,
        )

        assert isinstance(result, RefinedQuery)
        assert result.refined_query == query
        assert result.objective == query

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_query_generation_agent__returns_refined_query__when_mode_is_basic(
        self, mocker: Any
    ) -> None:
        """
        Purpose: Verify query_generation_agent returns a RefinedQuery when mode is BASIC.
        Why this matters: BASIC mode should return a single refined query.
        Setup summary: Mock LLM response with RefinedQuery.
        """
        query = "test query"
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "objective": "Find test info",
            "refined_query": "optimized test query",
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        result = await query_generation_agent(
            query=query,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            system_prompt="test prompt",
            mode=RefineQueryMode.BASIC,
        )

        assert isinstance(result, RefinedQuery)
        assert result.refined_query == "optimized test query"
        assert result.objective == "Find test info"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_query_generation_agent__returns_refined_queries__when_mode_is_advanced(
        self, mocker: Any
    ) -> None:
        """
        Purpose: Verify query_generation_agent returns RefinedQueries when mode is ADVANCED.
        Why this matters: ADVANCED mode should return multiple refined queries.
        Setup summary: Mock LLM response with RefinedQueries.
        """
        query = "test query"
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "objective": "Find test info",
            "refined_queries": [
                {"objective": "Sub objective 1", "refined_query": "query 1"},
                {"objective": "Sub objective 2", "refined_query": "query 2"},
            ],
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        result = await query_generation_agent(
            query=query,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            system_prompt="test prompt",
            mode=RefineQueryMode.ADVANCED,
        )

        assert isinstance(result, RefinedQueries)
        assert len(result.refined_queries) == 2
        assert result.refined_queries[0].refined_query == "query 1"
        assert result.refined_queries[1].refined_query == "query 2"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_query_generation_agent__raises_value_error__when_response_is_none(
        self, mocker: Any
    ) -> None:
        """
        Purpose: Verify query_generation_agent raises ValueError when LLM returns None.
        Why this matters: Ensures proper error handling for invalid LLM responses.
        Setup summary: Mock LLM response with None parsed value.
        """
        query = "test query"
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = None
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="Failed to parse insights"):
            await query_generation_agent(
                query=query,
                language_model_service=mock_lm_service,
                language_model=mock_lm,
                system_prompt="test prompt",
                mode=RefineQueryMode.BASIC,
            )


class TestWebSearchV1ExecutorInit:
    """Tests for WebSearchV1Executor initialization."""

    @pytest.mark.ai
    def test_init__creates_executor__with_required_parameters(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """
        Purpose: Verify WebSearchV1Executor initializes correctly with all required parameters.
        Why this matters: Ensures proper initialization of the executor.
        Setup summary: Provide all required dependencies.
        """
        tool_parameters = WebSearchToolParameters(query="test")

        executor = WebSearchV1Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
            refine_query_system_prompt="test prompt",
            refine_query_language_model=mock_executor_dependencies["language_model"],
        )

        assert executor.company_id == "test-company"
        assert executor.mode == RefineQueryMode.BASIC
        assert executor.max_queries == 10
        assert executor.tool_parameters == tool_parameters


class TestWebSearchV1ExecutorRun:
    """Tests for WebSearchV1Executor.run() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__returns_content_chunks_and_log_entries__when_search_succeeds(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_results: list[WebSearchResult],
        sample_content_chunks: list,
    ) -> None:
        """
        Purpose: Verify run() returns content chunks and log entries on successful execution.
        Why this matters: Ensures the main execution flow works correctly.
        Setup summary: Mock all services to return successful results.
        """
        tool_parameters = WebSearchToolParameters(query="test query")

        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=sample_web_search_results
        )
        mock_executor_dependencies["search_service"].requires_scraping = False
        mock_executor_dependencies["content_processor"].run = AsyncMock(return_value=[])
        mock_executor_dependencies["chunk_relevancy_sort_config"].enabled = False
        mock_executor_dependencies["content_reducer"].return_value = []

        executor = WebSearchV1Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
            refine_query_system_prompt="test prompt",
            refine_query_language_model=mock_executor_dependencies["language_model"],
            mode=RefineQueryMode.DEACTIVATED,
        )

        content_chunks = await executor.run()

        assert isinstance(content_chunks, list)
        mock_executor_dependencies["search_service"].search.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__crawls_urls__when_search_service_requires_scraping(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify run() crawls URLs when search service requires scraping.
        Why this matters: Some search engines don't return content, requiring crawling.
        Setup summary: Set requires_scraping=True on search service.
        """
        tool_parameters = WebSearchToolParameters(query="test query")

        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=sample_web_search_results
        )
        mock_executor_dependencies["search_service"].requires_scraping = True
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            return_value=["content1", "content2"]
        )
        mock_executor_dependencies["content_processor"].run = AsyncMock(return_value=[])
        mock_executor_dependencies["chunk_relevancy_sort_config"].enabled = False
        mock_executor_dependencies["content_reducer"].return_value = []

        executor = WebSearchV1Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
            refine_query_system_prompt="test prompt",
            refine_query_language_model=mock_executor_dependencies["language_model"],
            mode=RefineQueryMode.DEACTIVATED,
        )

        await executor.run()

        mock_executor_dependencies["crawler_service"].crawl.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__raises__when_search_result_url_is_blocked_before_crawl(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """
        Purpose: Verify V1 blocks unsafe search-result URLs when crawling is attempted.
        Why this matters: Search-driven crawl flows must not bypass the shared SSRF guard.
        Setup summary: Return a localhost URL from the search service with scraping enabled and assert CrawlTargetValidationError is raised.
        """
        tool_parameters = WebSearchToolParameters(query="test query")

        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=[
                WebSearchResult(
                    url="https://localhost/internal",
                    title="Local page",
                    snippet="Unsafe",
                    content="",
                )
            ]
        )
        mock_executor_dependencies["search_service"].requires_scraping = True
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            side_effect=UrlSafetyService.validate_batch_urls
        )

        executor = WebSearchV1Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
            refine_query_system_prompt="test prompt",
            refine_query_language_model=mock_executor_dependencies["language_model"],
            mode=RefineQueryMode.DEACTIVATED,
        )

        with pytest.raises(CrawlTargetValidationError):
            await executor.run()


class TestWebSearchExecutorSelectRelevantSources:
    """Tests for BaseWebSearchExecutor._select_relevant_sources()."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_select_relevant_sources__records_relevancy_invocation_stats(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """
        Purpose: Verify per-chunk relevancy-sort LLM usage is merged into the
            active WebSearch stats scope.
        Why this matters: The relevancy sorter makes one LLM call per chunk;
            those tokens were previously discarded, undercounting analytics.
        Setup summary: Return a sorter result carrying invocation_stats on its
            relevancies and assert they land in the scope.
        """
        from unique_toolkit.agentic.evaluation.schemas import (
            EvaluationMetricName,
            EvaluationMetricResult,
        )
        from unique_toolkit.language_model.invocation_stats import (
            LanguageModelInvocationStats,
        )
        from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

        from unique_web_search.invocation_stats import invocation_stats_scope

        stat = LanguageModelInvocationStats.from_usage(
            model_name="gpt-4",
            token_usage=LanguageModelTokenUsage(total_tokens=5),
            source="chunk_relevancy_sorter",
        )
        relevancy = Mock()
        relevancy.relevancy = EvaluationMetricResult(
            name=EvaluationMetricName.CONTEXT_RELEVANCY,
            value="high",
            reason="relevant",
            is_positive=True,
            invocation_stats=[stat],
        )
        sorter_result = Mock()
        sorter_result.relevancies = [relevancy]
        sorter_result.content_chunks = []
        sorter_result.user_message = "sorted"

        mock_executor_dependencies["chunk_relevancy_sorter"].run = AsyncMock(
            return_value=sorter_result
        )
        mock_executor_dependencies["content_reducer"].return_value = []

        executor = WebSearchV1Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=WebSearchToolParameters(query="test"),
            refine_query_system_prompt="test prompt",
            refine_query_language_model=mock_executor_dependencies["language_model"],
        )

        with invocation_stats_scope() as invocation_stats:
            await executor._select_relevant_sources(objective="obj", web_page_chunks=[])

        assert len(invocation_stats) == 1
        assert invocation_stats[0].source == "chunk_relevancy_sorter"
        assert invocation_stats[0].token_usage.total_tokens == 5


class TestWebSearchV1ExecutorRefineQuery:
    """Tests for WebSearchV1Executor._refine_query() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_refine_query__returns_single_query__when_mode_is_basic(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """
        Purpose: Verify _refine_query returns a single query when mode is BASIC.
        Why this matters: BASIC mode should return one refined query.
        Setup summary: Mock LLM to return a RefinedQuery.
        """
        tool_parameters = WebSearchToolParameters(query="test")

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "objective": "test objective",
            "refined_query": "refined test",
        }
        mock_executor_dependencies["language_model_service"].complete_async = AsyncMock(
            return_value=mock_response
        )

        executor = WebSearchV1Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
            refine_query_system_prompt="test prompt",
            refine_query_language_model=mock_executor_dependencies["language_model"],
            mode=RefineQueryMode.BASIC,
        )

        queries, objective = await executor._refine_query("test query")

        assert len(queries) == 1
        assert queries[0] == "refined test"
        assert objective == "test objective"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_refine_query__returns_multiple_queries__when_mode_is_advanced(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """
        Purpose: Verify _refine_query returns multiple queries when mode is ADVANCED.
        Why this matters: ADVANCED mode should return multiple refined queries.
        Setup summary: Mock LLM to return RefinedQueries.
        """
        tool_parameters = WebSearchToolParameters(query="test")

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "objective": "test objective",
            "refined_queries": [
                {"objective": "sub1", "refined_query": "query1"},
                {"objective": "sub2", "refined_query": "query2"},
            ],
        }
        mock_executor_dependencies["language_model_service"].complete_async = AsyncMock(
            return_value=mock_response
        )

        executor = WebSearchV1Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
            refine_query_system_prompt="test prompt",
            refine_query_language_model=mock_executor_dependencies["language_model"],
            mode=RefineQueryMode.ADVANCED,
        )

        queries, objective = await executor._refine_query("test query")

        assert len(queries) == 2
        assert queries[0] == "query1"
        assert queries[1] == "query2"
        assert objective == "test objective"


class TestWebSearchV1ExecutorEnforceMaxQueries:
    """Tests for WebSearchV1Executor._enforce_max_queries() method."""

    @pytest.mark.ai
    def test_enforce_max_queries__returns_all_queries__when_under_limit(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """
        Purpose: Verify _enforce_max_queries returns all queries when under the limit.
        Why this matters: Queries under the limit should not be truncated.
        Setup summary: Provide queries list smaller than max_queries.
        """
        tool_parameters = WebSearchToolParameters(query="test")

        executor = WebSearchV1Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
            refine_query_system_prompt="test prompt",
            refine_query_language_model=mock_executor_dependencies["language_model"],
            max_queries=5,
        )

        queries = ["q1", "q2", "q3"]
        result = executor._enforce_max_queries(queries)

        assert len(result) == 3
        assert result == queries

    @pytest.mark.ai
    def test_enforce_max_queries__truncates_queries__when_over_limit(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """
        Purpose: Verify _enforce_max_queries truncates queries when over the limit.
        Why this matters: Prevents excessive queries that could slow down execution.
        Setup summary: Provide queries list larger than max_queries.
        """
        tool_parameters = WebSearchToolParameters(query="test")

        executor = WebSearchV1Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
            refine_query_system_prompt="test prompt",
            refine_query_language_model=mock_executor_dependencies["language_model"],
            max_queries=3,
        )

        queries = ["q1", "q2", "q3", "q4", "q5"]
        result = executor._enforce_max_queries(queries)

        assert len(result) == 3
        assert result == ["q1", "q2", "q3"]


class TestWebSearchV2ExecutorInit:
    """Tests for WebSearchV2Executor initialization."""

    @pytest.mark.ai
    def test_init__creates_executor__with_required_parameters(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
    ) -> None:
        """
        Purpose: Verify WebSearchV2Executor initializes correctly with all required parameters.
        Why this matters: Ensures proper initialization of the executor.
        Setup summary: Provide all required dependencies.
        """
        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        assert executor.company_id == "test-company"
        assert executor.max_steps == 3
        assert executor.tool_parameters == sample_web_search_plan


class TestWebSearchV2ExecutorRun:
    """Tests for WebSearchV2Executor.run() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__returns_content_chunks_and_log_entries__when_execution_succeeds(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify run() returns content chunks and log entries on successful execution.
        Why this matters: Ensures the main execution flow works correctly.
        Setup summary: Mock all services to return successful results.
        """
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=sample_web_search_results
        )
        mock_executor_dependencies["search_service"].requires_scraping = False
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            return_value=["crawled content"]
        )
        mock_executor_dependencies["content_processor"].run = AsyncMock(return_value=[])
        mock_executor_dependencies["chunk_relevancy_sort_config"].enabled = False
        mock_executor_dependencies["content_reducer"].return_value = []

        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        content_chunks = await executor.run()

        assert isinstance(content_chunks, list)


class TestWebSearchV2ExecutorExecuteStep:
    """Tests for WebSearchV2Executor._execute_step() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_step__calls_search_step__when_step_type_is_search(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify _execute_step calls _execute_search_step for SEARCH step type.
        Why this matters: Ensures correct step routing based on step type.
        Setup summary: Create SEARCH step and verify search method is called.
        """
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=sample_web_search_results
        )
        mock_executor_dependencies["search_service"].requires_scraping = False
        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        step = Step(
            step_type=StepType.SEARCH,
            objective="Test search",
            query_or_url="test query",
        )

        result = await executor._execute_step(step)

        assert isinstance(result, list)
        mock_executor_dependencies["search_service"].search.assert_called_once_with(
            "test query"
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_step__calls_read_url_step__when_step_type_is_read_url(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
    ) -> None:
        """
        Purpose: Verify _execute_step calls _execute_read_url_step for READ_URL step type.
        Why this matters: Ensures correct step routing based on step type.
        Setup summary: Create READ_URL step and verify crawler is called.
        """
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            return_value=["content"]
        )
        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        step = Step(
            step_type=StepType.READ_URL,
            objective="Read page",
            query_or_url="https://example.com",
        )

        result = await executor._execute_step(step)

        assert isinstance(result, list)
        mock_executor_dependencies["crawler_service"].crawl.assert_called_once_with(
            ["https://example.com"]
        )


class TestWebSearchV2ExecutorExecuteSearchStep:
    """Tests for WebSearchV2Executor._execute_search_step() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_search_step__returns_search_results__when_no_scraping_required(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify _execute_search_step returns results without crawling when scraping not required.
        Why this matters: Some search engines return content directly.
        Setup summary: Set requires_scraping=False on search service.
        """
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=sample_web_search_results
        )
        mock_executor_dependencies["search_service"].requires_scraping = False
        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        step = Step(
            step_type=StepType.SEARCH,
            objective="Test search",
            query_or_url="test query",
        )

        result = await executor._execute_search_step(step)

        assert result == sample_web_search_results
        mock_executor_dependencies["crawler_service"].crawl.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_search_step__crawls_urls__when_scraping_required(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify _execute_search_step crawls URLs when search service requires scraping.
        Why this matters: Some search engines don't return content.
        Setup summary: Set requires_scraping=True on search service.
        """
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=sample_web_search_results
        )
        mock_executor_dependencies["search_service"].requires_scraping = True
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            return_value=["content1", "content2"]
        )
        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        step = Step(
            step_type=StepType.SEARCH,
            objective="Test search",
            query_or_url="test query",
        )

        result = await executor._execute_search_step(step)

        assert len(result) == 2
        mock_executor_dependencies["crawler_service"].crawl.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_search_step__raises__when_search_result_url_is_blocked(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
    ) -> None:
        """
        Purpose: Verify crawl handoff rejects unsafe search-result URLs when crawling is attempted.
        Why this matters: Search engines remain untrusted input sources and must not bypass the SSRF guard.
        Setup summary: Return a metadata URL from the search service, require scraping, and assert CrawlTargetValidationError is raised.
        """
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=[
                WebSearchResult(
                    url="http://169.254.169.254/latest/meta-data",
                    title="Metadata",
                    snippet="Unsafe",
                    content="",
                )
            ]
        )
        mock_executor_dependencies["search_service"].requires_scraping = True
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            side_effect=UrlSafetyService.validate_batch_urls
        )

        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        step = Step(
            step_type=StepType.SEARCH,
            objective="Test search",
            query_or_url="test query",
        )

        with pytest.raises(CrawlTargetValidationError):
            await executor._execute_search_step(step)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_search_step__adds_log_entry__after_search(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify _execute_search_step adds a log entry for the search.
        Why this matters: Log entries are needed for tracking and debugging.
        Setup summary: Execute search step and check queries_for_log.
        """
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=sample_web_search_results
        )
        mock_executor_dependencies["search_service"].requires_scraping = False
        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        step = Step(
            step_type=StepType.SEARCH,
            objective="Test search",
            query_or_url="test query",
        )

        await executor._execute_search_step(step)

        # Verify message log callback was called for logging the search
        mock_executor_dependencies[
            "message_log_callback"
        ].log_web_search_results.assert_called()


class TestWebSearchV3ExecutorSearch:
    """Tests for WebSearchV3Executor ``search`` (SERP-only JSON chunks)."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_search__returns_json_chunks_without_crawl(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """V3 search maps SERP rows to ContentChunks with JSON bodies; no crawl or judge."""
        import json

        tool_parameters = WebSearchV3ToolParameters.model_validate(
            {
                "command": "search",
                "phase": "target",
                "payload": {
                    "gap": "Need fresh NVIDIA press coverage",
                    "query": "nvidia coverage",
                },
            }
        )

        serp = [
            WebSearchResult(
                url="https://example.com/page1",
                title="Page 1",
                snippet="Snippet 1",
                content="",
            ),
            WebSearchResult(
                url="https://example.com/page2",
                title="Page 2",
                snippet="Snippet 2",
                content="",
            ),
        ]
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock()

        executor = WebSearchV3Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
        )
        result = await executor.run()

        mock_executor_dependencies["crawler_service"].crawl.assert_not_called()
        assert len(result) == 2
        first = json.loads(result[0].text)
        assert first["url"] == "https://example.com/page1"
        assert first["domain"] == "example.com"
        assert first["title"] == "Page 1"
        assert first["snippet"] == "Snippet 1"


class TestWebSearchV3ExecutorFetchUrls:
    """Tests for WebSearchV3Executor ``read_urls`` (crawl + content pipeline)."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_fetch_urls__invokes_crawler_not_search(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """V3 read_urls calls the crawler with the supplied URLs and skips the search engine."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
        ]
        tool_parameters = WebSearchV3ToolParameters.model_validate(
            {
                "command": "read_urls",
                "phase": "target",
                "payload": {"urls": urls},
            }
        )

        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            return_value=["content1", "content2"]
        )
        mock_executor_dependencies["content_processor"].run = AsyncMock(return_value=[])
        mock_executor_dependencies["chunk_relevancy_sort_config"].enabled = False
        mock_executor_dependencies["content_reducer"].return_value = []

        executor = WebSearchV3Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
        )
        result = await executor.run()

        mock_executor_dependencies["crawler_service"].crawl.assert_called_once_with(
            urls
        )
        mock_executor_dependencies["search_service"].search.assert_not_called()
        mock_executor_dependencies["content_processor"].run.assert_awaited_once()
        assert isinstance(result, list)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_fetch_urls__raises__when_payload_contains_blocked_url(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """
        Purpose: Verify V3 read_urls rejects blocked targets when crawling is attempted.
        Why this matters: Direct URL reads are the highest-risk ingress for SSRF-style abuse.
        Setup summary: Provide a localhost URL in the payload and assert CrawlTargetValidationError is raised.
        """
        tool_parameters = WebSearchV3ToolParameters.model_validate(
            {
                "command": "read_urls",
                "phase": "target",
                "payload": {"urls": ["https://localhost/internal"]},
            }
        )
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            side_effect=UrlSafetyService.validate_batch_urls
        )

        executor = WebSearchV3Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=tool_parameters,
        )

        with pytest.raises(CrawlTargetValidationError):
            await executor.run()


class TestWebSearchV3ToolParametersValidation:
    """Validators on the V3 tool parameter schema (``command``/``phase``/``payload``)."""

    @pytest.mark.ai
    def test_search_command_with_search_payload_parses(self) -> None:
        """``command='search'`` with a ``SearchPayload`` validates and round-trips."""
        params = WebSearchV3ToolParameters.model_validate(
            {
                "command": "search",
                "phase": "target",
                "payload": {
                    "gap": "Need the current target rate",
                    "query": "fed funds rate",
                },
            }
        )
        assert params.command == Command.SEARCH
        assert isinstance(params.payload, SearchPayload)
        assert params.payload.query == "fed funds rate"

    @pytest.mark.ai
    def test_read_urls_command_with_fetch_urls_payload_parses(self) -> None:
        """``command='read_urls'`` with a ``FetchUrlsPayload`` validates and round-trips."""
        params = WebSearchV3ToolParameters.model_validate(
            {
                "command": "read_urls",
                "phase": "target",
                "payload": {
                    "urls": [
                        "https://www.sec.gov/Archives/edgar/data/foo/10-k.htm",
                    ],
                },
            }
        )
        assert params.command == Command.FETCH_URLS
        assert isinstance(params.payload, FetchUrlsPayload)
        assert params.payload.urls == [
            "https://www.sec.gov/Archives/edgar/data/foo/10-k.htm",
        ]

    @pytest.mark.ai
    def test_extra_fields_are_rejected(self) -> None:
        """Top-level ``extra='forbid'`` rejects unknown keys (no legacy fields allowed)."""
        with pytest.raises(ValueError):
            WebSearchV3ToolParameters.model_validate(
                {
                    "command": "search",
                    "phase": "target",
                    "payload": {"gap": "g", "query": "q"},
                    "task_complexity": "simple",
                }
            )

    @pytest.mark.ai
    def test_objective_field_is_rejected(self) -> None:
        """Legacy ``objective`` is replaced by ``phase``."""
        with pytest.raises(ValueError):
            WebSearchV3ToolParameters.model_validate(
                {
                    "command": "search",
                    "objective": "Look up rate",
                    "payload": {"gap": "g", "query": "q"},
                }
            )

    @pytest.mark.ai
    def test_command_enum_values(self) -> None:
        """The ``Command`` enum exposes exactly ``search`` and ``read_urls``."""
        assert Command("search") is Command.SEARCH
        assert Command("read_urls") is Command.FETCH_URLS

    @pytest.mark.ai
    def test_v3_strategy_build_display_name_per_command(self) -> None:
        """V3 strategy appends a command-specific phase suffix to the display name."""
        from unique_web_search.services.executors.v3.config import WebSearchV3Config
        from unique_web_search.services.executors.v3.strategy import WebSearchV3Strategy

        search_params = WebSearchV3ToolParameters.model_validate(
            {
                "command": "search",
                "phase": "exploratory",
                "payload": {"gap": "g", "query": "q"},
            }
        )
        fetch_params = WebSearchV3ToolParameters.model_validate(
            {
                "command": "read_urls",
                "phase": "target",
                "payload": {"urls": ["https://example.com/a"]},
            }
        )
        strategy = WebSearchV3Strategy(WebSearchV3Config())
        assert search_params.relevance_focus() == "[exploratory] g"
        assert (
            strategy.build_display_name(
                base_display_name="Web Search",
                parameters=search_params,
            )
            == "Web - Searching"
        )
        assert (
            strategy.build_display_name(
                base_display_name="Web Search",
                parameters=fetch_params,
            )
            == "Web - Reading Pages"
        )


class TestWebSearchV2ExecutorExecuteReadUrlStep:
    """Tests for WebSearchV2Executor._execute_read_url_step() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_read_url_step__returns_web_search_results__with_crawled_content(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
    ) -> None:
        """
        Purpose: Verify _execute_read_url_step returns WebSearchResult with crawled content.
        Why this matters: READ_URL steps should return properly structured results.
        Setup summary: Mock crawler to return content.
        """
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            return_value=["Test page content"]
        )
        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        step = Step(
            step_type=StepType.READ_URL,
            objective="Read documentation",
            query_or_url="https://example.com/docs",
        )

        result = await executor._execute_read_url_step(step)

        assert len(result) == 1
        assert result[0].url == "https://example.com/docs"
        assert result[0].content == "Test page content"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_read_url_step__adds_log_entry__after_crawl(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
    ) -> None:
        """
        Purpose: Verify _execute_read_url_step adds a log entry for the URL read.
        Why this matters: Log entries are needed for tracking and debugging.
        Setup summary: Execute read URL step and check queries_for_log.
        """
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            return_value=["content"]
        )
        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        step = Step(
            step_type=StepType.READ_URL,
            objective="Read page",
            query_or_url="https://example.com",
        )

        await executor._execute_read_url_step(step)

        # Verify message log callback was called for logging progress
        mock_executor_dependencies[
            "message_log_callback"
        ].log_web_search_results.assert_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_read_url_step__raises__when_target_url_is_blocked(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
    ) -> None:
        """
        Purpose: Verify READ_URL steps reject blocked targets when crawling is attempted.
        Why this matters: The direct URL-read path must not allow localhost or private-network access.
        Setup summary: Execute a READ_URL step pointing at localhost and assert CrawlTargetValidationError is raised.
        """
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            side_effect=UrlSafetyService.validate_batch_urls
        )

        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        step = Step(
            step_type=StepType.READ_URL,
            objective="Read page",
            query_or_url="https://localhost/private",
        )

        with pytest.raises(CrawlTargetValidationError):
            await executor._execute_read_url_step(step)


class TestWebSearchV2ExecutorEnforceMaxSteps:
    """Tests for WebSearchV2Executor._enforce_max_steps() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_enforce_max_steps__does_not_truncate__when_under_limit(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """
        Purpose: Verify _enforce_max_steps doesn't truncate steps when under the limit.
        Why this matters: Steps under the limit should not be modified.
        Setup summary: Create plan with fewer steps than max_steps.
        """
        plan = WebSearchPlan(
            objective="Test",
            query_analysis="Analysis",
            steps=[
                Step(step_type=StepType.SEARCH, objective="s1", query_or_url="q1"),
                Step(step_type=StepType.SEARCH, objective="s2", query_or_url="q2"),
            ],
            expected_outcome="Outcome",
        )

        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=plan,
            max_steps=5,
        )

        await executor._enforce_max_steps()

        assert len(executor.tool_parameters.steps) == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_enforce_max_steps__truncates_steps__when_over_limit(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """
        Purpose: Verify _enforce_max_steps truncates steps when over the limit.
        Why this matters: Prevents excessive steps that could slow down execution.
        Setup summary: Create plan with more steps than max_steps.
        """
        plan = WebSearchPlan(
            objective="Test",
            query_analysis="Analysis",
            steps=[
                Step(step_type=StepType.SEARCH, objective="s1", query_or_url="q1"),
                Step(step_type=StepType.SEARCH, objective="s2", query_or_url="q2"),
                Step(step_type=StepType.SEARCH, objective="s3", query_or_url="q3"),
                Step(step_type=StepType.SEARCH, objective="s4", query_or_url="q4"),
                Step(step_type=StepType.SEARCH, objective="s5", query_or_url="q5"),
            ],
            expected_outcome="Outcome",
        )

        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=plan,
            max_steps=3,
        )

        await executor._enforce_max_steps()

        assert len(executor.tool_parameters.steps) == 3
        # Verify debug info was added
        assert any(
            step.step_name == "enforce_max_steps" for step in executor.debug_info.steps
        )


class TestWebSearchV2ExecutorDebugInfo:
    """Tests for WebSearchV2Executor debug info tracking."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_search_step__adds_debug_info__for_each_operation(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
        sample_web_search_plan: WebSearchPlan,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify _execute_search_step adds debug info for search operations.
        Why this matters: Debug info is essential for troubleshooting.
        Setup summary: Execute search step and verify debug_info.steps.
        """
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=sample_web_search_results
        )
        mock_executor_dependencies["search_service"].requires_scraping = False
        executor = WebSearchV2Executor(
            services=executor_context_objects["services"],
            config=executor_context_objects["config"],
            callbacks=executor_context_objects["callbacks"],
            tool_call=mock_executor_dependencies["tool_call"],
            tool_parameters=sample_web_search_plan,
        )

        step = Step(
            step_type=StepType.SEARCH,
            objective="Test",
            query_or_url="test query",
        )

        await executor._execute_search_step(step)

        # Should have step name debug info and search debug info
        assert len(executor.debug_info.steps) >= 1
        search_step = next(
            (s for s in executor.debug_info.steps if ".search" in s.step_name), None
        )
        assert search_step is not None
        assert search_step.extra["query"] == "test query"
