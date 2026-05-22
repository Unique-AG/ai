"""Tests for WebSearchV1Executor, WebSearchV2Executor, and WebSearchV3Executor."""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

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
from unique_web_search.services.url_safety import (
    CrawlTargetValidationError,
    validate_crawl_urls,
)


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
        tool_parameters = WebSearchToolParameters(query="test", date_restrict=None)

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
        tool_parameters = WebSearchToolParameters(
            query="test query", date_restrict=None
        )

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
        tool_parameters = WebSearchToolParameters(
            query="test query", date_restrict=None
        )

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
        tool_parameters = WebSearchToolParameters(
            query="test query", date_restrict=None
        )

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
            side_effect=validate_crawl_urls
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
        tool_parameters = WebSearchToolParameters(query="test", date_restrict=None)

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
        tool_parameters = WebSearchToolParameters(query="test", date_restrict=None)

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
        tool_parameters = WebSearchToolParameters(query="test", date_restrict=None)

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
        tool_parameters = WebSearchToolParameters(query="test", date_restrict=None)

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
        mock_executor_dependencies[
            "search_service"
        ].config.search_engine_name.name = "TEST"

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
        mock_executor_dependencies["crawler_service"].config.crawler_type.name = "TEST"

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
        mock_executor_dependencies[
            "search_service"
        ].config.search_engine_name.name = "TEST"

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
        mock_executor_dependencies[
            "search_service"
        ].config.search_engine_name.name = "TEST"
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            return_value=["content1", "content2"]
        )
        mock_executor_dependencies["crawler_service"].config.crawler_type.name = "TEST"

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
        mock_executor_dependencies[
            "search_service"
        ].config.search_engine_name.name = "TEST"
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            side_effect=validate_crawl_urls
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
        mock_executor_dependencies[
            "search_service"
        ].config.search_engine_name.name = "TEST"

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
                "objective": "Find recent search hits about NVIDIA coverage",
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
        mock_executor_dependencies[
            "search_service"
        ].config.search_engine_name.name = "TEST"
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


class TestWebSearchV3ExecutorSerpFilter:
    """Tests for the SERP relevance filter wiring inside ``_run_search``."""

    @staticmethod
    def _make_executor(executor_context, deps, tool_parameters, serp_filter_config):
        return WebSearchV3Executor(
            services=executor_context["services"],
            config=executor_context["config"],
            callbacks=executor_context["callbacks"],
            tool_call=deps["tool_call"],
            tool_parameters=tool_parameters,
            serp_filter_config=serp_filter_config,
        )

    @staticmethod
    def _make_serp(n: int) -> list:
        return [
            WebSearchResult(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                snippet=f"Snippet {i}",
                content="",
            )
            for i in range(n)
        ]

    @staticmethod
    def _make_search_params() -> WebSearchV3ToolParameters:
        return WebSearchV3ToolParameters.model_validate(
            {
                "command": "search",
                "objective": "Find authoritative sources about NVIDIA Q4 revenue",
                "payload": {
                    "gap": "NVIDIA Q4 2025 revenue figure",
                    "query": "nvidia q4 2025 revenue",
                },
            }
        )

    @pytest.mark.asyncio
    async def test_run_search__filter_disabled_returns_results_unchanged(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """When ``SerpFilterConfig.enabled=False``, no LLM call is made and all results are returned."""
        import json

        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(4)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        lm_service.complete_async = AsyncMock()  # would fail loudly if called

        disabled_cfg = SerpFilterConfig(enabled=False)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            disabled_cfg,
        )

        result = await executor.run()

        lm_service.complete_async.assert_not_called()
        assert len(result) == len(serp)
        assert [json.loads(c.text)["url"] for c in result] == [r.url for r in serp]

    @pytest.mark.asyncio
    async def test_run_search__filter_short_circuits_on_single_result_when_min_score_zero(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """One result + ``min_score=0`` skips the LLM call (nothing to rank or threshold)."""
        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(1)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        lm_service.complete_async = AsyncMock()

        cfg = SerpFilterConfig(enabled=True, min_score=0.0)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            cfg,
        )

        result = await executor.run()

        lm_service.complete_async.assert_not_called()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_run_search__filter_called_with_objective_query_gap(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """The judge prompt is rendered with the objective, query, and gap from the call."""
        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(3)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": i, "explanation": "ok", "relevance_score": 0.9}
                for i in range(3)
            ]
        }
        lm_service.complete_async = AsyncMock(return_value=mock_response)

        cfg = SerpFilterConfig(enabled=True, min_score=0.0)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            cfg,
        )

        await executor.run()

        lm_service.complete_async.assert_awaited_once()
        messages = lm_service.complete_async.call_args[0][0]
        user_content = (
            messages[1].content if hasattr(messages[1], "content") else str(messages[1])
        )
        assert "Find authoritative sources about NVIDIA Q4 revenue" in user_content
        assert "nvidia q4 2025 revenue" in user_content
        assert "NVIDIA Q4 2025 revenue figure" in user_content

    @pytest.mark.asyncio
    async def test_run_search__filter_drops_results_below_min_score(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """Results scored below ``min_score`` are excluded from the chunks returned to the model."""
        import json

        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(3)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Only index 0 clears the 0.5 threshold; 1 and 2 are dropped.
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "high", "relevance_score": 0.9},
                {"index": 1, "explanation": "low", "relevance_score": 0.2},
                {"index": 2, "explanation": "low", "relevance_score": 0.1},
            ]
        }
        lm_service.complete_async = AsyncMock(return_value=mock_response)

        cfg = SerpFilterConfig(enabled=True, min_score=0.5)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            cfg,
        )

        result = await executor.run()

        urls = [json.loads(c.text)["url"] for c in result]
        assert urls == ["https://example.com/page0"]

        # The debug step records per-URL judge scores for the kept set so
        # operators can see *why* the agent decided to fetch (or not).
        debug_steps = executor_context_objects["config"].debug_info.steps
        filter_steps = [s for s in debug_steps if s.step_name == "SEARCH.serp_filter"]
        assert len(filter_steps) == 1
        assert filter_steps[0].extra["kept_scores"] == {
            "https://example.com/page0": 0.9,
        }

    @pytest.mark.asyncio
    async def test_run_search__filter_fails_open_on_llm_exception(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """LLM exceptions never silently truncate — all original results are returned."""
        import json

        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(4)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        lm_service.complete_async = AsyncMock(
            side_effect=RuntimeError("downstream LLM error")
        )

        # ``max_results=2`` would have truncated under the old buggy fallback;
        # the new behavior returns all 4 unmodified.
        cfg = SerpFilterConfig(enabled=True, min_score=0.5, max_results=2)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            cfg,
        )

        result = await executor.run()

        urls = [json.loads(c.text)["url"] for c in result]
        assert urls == [r.url for r in serp]
        assert len(urls) == 4

    @pytest.mark.asyncio
    async def test_run_search__filter_falls_back_to_unfiltered_when_all_below_min_score(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """All scored below ``min_score`` → return the unfiltered SERP, never an empty list.

        The V3 system prompt tells the agent it can fetch URLs from the SERP it
        just saw; if the filter hid every URL when nothing scored well, the
        agent would have nothing to escalate to. Verify the fail-safe restores
        the original list and records ``fell_back_to_unfiltered=True`` in the
        debug step.
        """
        import json

        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(3)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Every result scores below the 0.5 threshold.
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "low", "relevance_score": 0.1},
                {"index": 1, "explanation": "low", "relevance_score": 0.2},
                {"index": 2, "explanation": "low", "relevance_score": 0.15},
            ]
        }
        lm_service.complete_async = AsyncMock(return_value=mock_response)

        cfg = SerpFilterConfig(enabled=True, min_score=0.5)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            cfg,
        )

        result = await executor.run()

        # All 3 original URLs are returned despite all scoring below the threshold.
        urls = [json.loads(c.text)["url"] for c in result]
        assert urls == [r.url for r in serp]

        # The debug step records the fall-back so operators can see it fired.
        debug_steps = executor_context_objects["config"].debug_info.steps
        filter_steps = [s for s in debug_steps if s.step_name == "SEARCH.serp_filter"]
        assert len(filter_steps) == 1
        assert filter_steps[0].extra["fell_back_to_unfiltered"] is True
        assert filter_steps[0].extra["before"] == 3
        assert filter_steps[0].extra["after"] == 3

    @pytest.mark.asyncio
    async def test_run_search__off_topic_serp_returns_reformulate_chunk(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """When the judge produces zero raw judgments (entire SERP off-topic),
        the executor surfaces a single synthetic ``ContentChunk`` with a
        ``serp_quality=off_topic`` payload and *no* URLs from the SERP.

        Previously this case fell open with the full unfiltered SERP — but
        production traces showed the URLs that triggered it were already-
        rejected LinkedIn profiles and Facebook posts that just confused
        the agent (or, worse, got fetched). The reformulate cue tells the
        agent ``serp_quality=off_topic`` + ``instructions=...`` and an empty
        ``url`` so it can't accidentally chase a rejected URL.
        """
        import json

        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(4)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # The off-topic signal: LLM judge structurally returned zero judgments.
        mock_response.choices[0].message.parsed = {"judgments": []}
        lm_service.complete_async = AsyncMock(return_value=mock_response)

        cfg = SerpFilterConfig(enabled=True, min_score=0.3)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            cfg,
        )

        result = await executor.run()

        # Exactly one synthetic chunk, no SERP URLs leak through.
        assert len(result) == 1
        chunk = result[0]
        assert chunk.url == ""
        assert chunk.title == "No relevant results — reformulate query"
        payload = json.loads(chunk.text)
        assert payload["serp_quality"] == "off_topic"
        # The agent-facing instructions should explicitly tell it *not* to
        # retry the same query — the whole point of this signal.
        assert "reformulate" in payload["instructions"].lower()
        # Make sure no rejected URL leaked into the payload anywhere.
        for r in serp:
            assert r.url not in chunk.text

    @pytest.mark.asyncio
    async def test_run_search__off_topic_serp_records_debug_step(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """The off-topic debug step replaces the misleading
        ``fell_back_to_unfiltered=True`` shape with a structured
        ``serp_quality="off_topic"`` flag and an ``after=0`` count.

        Operators looking at this step in the UI should be able to tell at
        a glance whether (a) the filter found nothing above threshold but
        the judge worked (the old fall-back path, still valid), or (b) the
        judge structurally signalled the SERP was off-topic (this path).
        Same step name, different ``extra`` fields.
        """
        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(3)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {"judgments": []}
        lm_service.complete_async = AsyncMock(return_value=mock_response)

        cfg = SerpFilterConfig(enabled=True, min_score=0.3)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            cfg,
        )

        await executor.run()

        debug_steps = executor_context_objects["config"].debug_info.steps
        filter_steps = [s for s in debug_steps if s.step_name == "SEARCH.serp_filter"]
        assert len(filter_steps) == 1
        extra = filter_steps[0].extra
        assert extra["serp_quality"] == "off_topic"
        assert extra["before"] == 3
        assert extra["after"] == 0
        assert extra["kept_urls"] == []
        assert extra["kept_scores"] == {}
        # All input URLs land in ``dropped_urls`` so the audit trail is
        # complete — operators can still see *which* URLs got rejected.
        assert set(extra["dropped_urls"]) == {r.url for r in serp}
        # The legacy ``fell_back_to_unfiltered`` flag should NOT appear in
        # this case — it'd be ambiguous (we didn't fall back, we routed to
        # a different signal).
        assert "fell_back_to_unfiltered" not in extra

    @pytest.mark.asyncio
    async def test_run_search__sanitizes_control_characters_in_query(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """C0/C1 control characters in the model's query are stripped before search."""
        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(2)
        search_mock = AsyncMock(return_value=serp)
        mock_executor_dependencies["search_service"].search = search_mock
        mock_executor_dependencies[
            "language_model_service"
        ].complete_async = AsyncMock()

        # Dirty query: Shift-Out + Vertical Tab interleaved with valid keywords
        # and a trailing run of control chars + whitespace.
        dirty_query = "Khlong Toei industrial land   "
        tool_parameters = WebSearchV3ToolParameters.model_validate(
            {
                "command": "search",
                "objective": "Find industrial land price",
                "payload": {
                    "gap": "Khlong Toei industrial price per sqm",
                    "query": dirty_query,
                },
            }
        )

        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            tool_parameters,
            SerpFilterConfig(enabled=False),
        )

        await executor.run()

        # The query passed to the search engine has no control characters,
        # no leading/trailing whitespace, and collapsed internal whitespace.
        search_mock.assert_awaited_once()
        passed_query = search_mock.call_args[0][0]
        assert passed_query == "Khlong Toei industrial land"

    @pytest.mark.asyncio
    async def test_run_search__control_chars_between_letters_do_not_merge_words(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """Control chars between word characters must NOT collapse adjacent words.

        Observed regression: the model emitted ``\\x1a\\x0e1\\x0ea\\x0e3\\x004Treasury``;
        stripping the control chars merged the digits into the next word as
        ``1a34Treasury``, which the engine matched as a nonsense token and the
        SERP came back empty. The fix replaces control chars with space so
        word boundaries survive, even if the resulting "1 a 3 4 Treasury" is
        ugly — Google then tokenizes the real words and the search has a chance.
        """
        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        search_mock = AsyncMock(return_value=[])
        mock_executor_dependencies["search_service"].search = search_mock

        # Exact pattern from the production BNPP trace.
        dirty_query = "\x1a\x0e1\x0ea\x0e3\x004Treasury Department Bangkok"
        tool_parameters = WebSearchV3ToolParameters.model_validate(
            {
                "command": "search",
                "objective": "Find appraisal",
                "payload": {"gap": "Bangkok land appraisal", "query": dirty_query},
            }
        )

        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            tool_parameters,
            SerpFilterConfig(enabled=False),
        )

        await executor.run()

        passed_query = search_mock.call_args[0][0]
        # The legitimate phrase "Treasury Department Bangkok" must be intact —
        # this is the win vs. the previous behavior of merging into ``1a34Treasury``.
        # (We can't recover separators the model didn't emit: ``\x004Treasury``
        # has no control char between ``4`` and ``T``, so ``4Treasury`` will
        # remain a single token. That's a model-output problem, not a
        # sanitizer problem.)
        assert "Treasury Department Bangkok" in passed_query
        # The pre-fix merged-token regression must not return.
        assert "1a34Treasury" not in passed_query

    @pytest.mark.asyncio
    async def test_run__no_control_chars_leak_into_debug_info_dump(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """LLM-supplied text in objective/gap/urls is sanitized before debug_info.

        Real failure: Postgres TEXT columns reject ``\\u0000`` (error 22P05).
        Before this fix we sanitized only ``query``; ``objective`` and ``gap``
        flowed straight into ``debug_info`` and crashed downstream
        ``modify_message`` / ``stream-responses`` with an opaque 500.

        Lock in: after a tool call with NUL bytes in every LLM-supplied field,
        the dumped debug_info must contain no NUL or other C0 control chars.
        """
        import json

        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        mock_executor_dependencies["search_service"].search = AsyncMock(return_value=[])

        # NUL bytes (the Postgres killer) plus assorted C0 chars in every
        # LLM-supplied field.
        tool_parameters = WebSearchV3ToolParameters.model_validate(
            {
                "command": "search",
                "objective": "Find\x00appraisal\x0evalues",
                "payload": {
                    "gap": "Khlong\x00Toei\x01prices",
                    "query": "Treasury\x00Department\x0e2024",
                },
            }
        )

        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            tool_parameters,
            SerpFilterConfig(enabled=False),
        )

        await executor.run()

        # Serialize the same way the orchestrator does before sending to the
        # backend; any control char here would crash the Postgres write.
        debug_dump = executor_context_objects["config"].debug_info.model_dump(
            with_debug_details=True
        )
        serialized = json.dumps(debug_dump, default=str)
        for forbidden in ("\x00", "\x01", "\x0e", "\x1f", "\x7f"):
            assert forbidden not in serialized, (
                f"Control char {forbidden!r} leaked into debug_info dump"
            )

    @pytest.mark.asyncio
    async def test_run_search__skips_engine_call_when_query_is_all_control_chars(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """A query that's *entirely* control/whitespace chars sanitizes to empty.

        Sending that to the engine wastes an API call and returns an empty SERP.
        The executor should detect the empty post-sanitize query, log an error,
        record a SEARCH.skipped debug step, and return no chunks — the agent
        sees "no results" and reformulates on the next turn.
        """
        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        search_mock = AsyncMock()
        mock_executor_dependencies["search_service"].search = search_mock

        # All C0/C1 controls + whitespace; sanitizer collapses to "".
        all_control = "\x0e\x0b\x01\x7f   \t\n"
        tool_parameters = WebSearchV3ToolParameters.model_validate(
            {
                "command": "search",
                "objective": "Find something",
                "payload": {
                    "gap": "Anything",
                    "query": all_control,
                },
            }
        )

        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            tool_parameters,
            SerpFilterConfig(enabled=False),
        )

        result = await executor.run()

        # Engine never called, no chunks returned.
        search_mock.assert_not_called()
        assert result == []

        # A SEARCH.skipped debug step is recorded so operators can see the
        # skip happened and why.
        debug_steps = executor_context_objects["config"].debug_info.steps
        skipped = [s for s in debug_steps if s.step_name == "SEARCH.skipped"]
        assert len(skipped) == 1
        assert skipped[0].config == "empty_query_after_sanitization"

    @pytest.mark.asyncio
    async def test_run_search__logs_filtered_results_not_raw_serp(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """``log_web_search_results`` is called with the filtered SERP (what the
        agent received), not the raw pre-filter list. This way the operator UI
        reflects the agent's actual context.
        """
        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(3)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Only index 1 clears the 0.5 threshold; 0 and 2 are dropped.
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "low", "relevance_score": 0.1},
                {"index": 1, "explanation": "high", "relevance_score": 0.9},
                {"index": 2, "explanation": "low", "relevance_score": 0.2},
            ]
        }
        lm_service.complete_async = AsyncMock(return_value=mock_response)

        log_results_mock = mock_executor_dependencies[
            "message_log_callback"
        ].log_web_search_results

        cfg = SerpFilterConfig(enabled=True, min_score=0.5)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            cfg,
        )

        await executor.run()

        # Called exactly once, with the filtered list (1 URL), not the raw 3.
        log_results_mock.assert_awaited_once()
        logged_results = log_results_mock.call_args[0][0]
        assert len(logged_results) == 1
        assert logged_results[0].url == "https://example.com/page1"

    @pytest.mark.asyncio
    async def test_run_search__filter_logs_progress_message(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """The filter surfaces progress to the user via the message log callback."""
        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(3)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": i, "explanation": "ok", "relevance_score": 0.9}
                for i in range(3)
            ]
        }
        lm_service.complete_async = AsyncMock(return_value=mock_response)

        cfg = SerpFilterConfig(enabled=True, min_score=0.0)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            cfg,
        )

        await executor.run()

        log_progress_calls = [
            c.args[0]
            for c in mock_executor_dependencies[
                "message_log_callback"
            ].log_progress.call_args_list
        ]
        assert any("Filtering" in msg for msg in log_progress_calls)

    @pytest.mark.asyncio
    async def test_run_search__chunk_payload_includes_relevance_score(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """When the SERP filter runs, each chunk's JSON carries ``relevance_score``.

        This is the signal the V3 prompt teaches the agent to use (≥0.85 → prefer
        fetch over another search). Without it the agent has nothing to trust.
        """
        import json

        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        # Distinct domains so the per-domain cap doesn't drop the 3rd result.
        serp = [
            WebSearchResult(
                url=f"https://site{i}.com/page",
                title=f"Page {i}",
                snippet=f"Snippet {i}",
                content="",
            )
            for i in range(3)
        ]
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )
        lm_service = mock_executor_dependencies["language_model_service"]
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "top", "relevance_score": 0.92},
                {"index": 1, "explanation": "mid", "relevance_score": 0.55},
                {"index": 2, "explanation": "weak", "relevance_score": 0.31},
            ]
        }
        lm_service.complete_async = AsyncMock(return_value=mock_response)

        cfg = SerpFilterConfig(enabled=True, min_score=0.0)
        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            cfg,
        )

        chunks = await executor.run()

        scores_by_url = {
            json.loads(c.text)["url"]: json.loads(c.text).get("relevance_score")
            for c in chunks
        }
        # Two decimals — matches the rounding in _serp_results_to_content_chunks.
        assert scores_by_url["https://site0.com/page"] == 0.92
        assert scores_by_url["https://site1.com/page"] == 0.55
        assert scores_by_url["https://site2.com/page"] == 0.31

    @pytest.mark.asyncio
    async def test_run_search__chunk_payload_omits_score_when_filter_disabled(
        self,
        executor_context_objects: dict,
        mock_executor_dependencies: dict,
    ) -> None:
        """Filter disabled → no ``relevance_score`` key in the chunk JSON (agent reads as 'absent')."""
        import json

        from unique_web_search.services.executors.v3.config import SerpFilterConfig

        serp = self._make_serp(2)
        mock_executor_dependencies["search_service"].search = AsyncMock(
            return_value=serp
        )

        executor = self._make_executor(
            executor_context_objects,
            mock_executor_dependencies,
            self._make_search_params(),
            SerpFilterConfig(enabled=False),
        )

        chunks = await executor.run()

        for c in chunks:
            assert "relevance_score" not in json.loads(c.text)


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
                "objective": "Read the linked articles for full text",
                "payload": {"urls": urls},
            }
        )

        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            return_value=["content1", "content2"]
        )
        mock_executor_dependencies["crawler_service"].config.crawler_type.name = "TEST"
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
                "objective": "Read the linked articles for full text",
                "payload": {"urls": ["https://localhost/internal"]},
            }
        )
        mock_executor_dependencies["crawler_service"].crawl = AsyncMock(
            side_effect=validate_crawl_urls
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
    """Validators on the V3 tool parameter schema (``command``/``objective``/``payload``)."""

    @pytest.mark.ai
    def test_search_command_with_search_payload_parses(self) -> None:
        """``command='search'`` with a ``SearchPayload`` validates and round-trips."""
        params = WebSearchV3ToolParameters.model_validate(
            {
                "command": "search",
                "objective": "Look up the current Fed funds target rate.",
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
                "objective": "Read the linked SEC filing for exact figures.",
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
                    "objective": "Anything",
                    "payload": {"gap": "g", "query": "q"},
                    "task_complexity": "simple",
                }
            )

    @pytest.mark.ai
    def test_command_enum_values(self) -> None:
        """The ``Command`` enum exposes exactly ``search`` and ``read_urls``."""
        assert Command("search") is Command.SEARCH
        assert Command("read_urls") is Command.FETCH_URLS

    @pytest.mark.ai
    def test_get_display_name_suffix_per_command(self) -> None:
        """Display-name suffix differs per command for UI clarity."""
        search_params = WebSearchV3ToolParameters.model_validate(
            {
                "command": "search",
                "objective": "Search obj",
                "payload": {"gap": "g", "query": "q"},
            }
        )
        fetch_params = WebSearchV3ToolParameters.model_validate(
            {
                "command": "read_urls",
                "objective": "Fetch obj",
                "payload": {"urls": ["https://example.com/a"]},
            }
        )
        assert search_params.get_display_name_suffix() == " - Searching"
        assert fetch_params.get_display_name_suffix() == " - Reading Pages"


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
        mock_executor_dependencies["crawler_service"].config.crawler_type.name = "TEST"

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
        mock_executor_dependencies["crawler_service"].config.crawler_type.name = "TEST"

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
            side_effect=validate_crawl_urls
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
        mock_executor_dependencies[
            "search_service"
        ].config.search_engine_name.name = "TEST"

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
