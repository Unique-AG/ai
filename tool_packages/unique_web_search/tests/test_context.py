"""Tests for executor context classes.

This module tests the context dataclasses and protocols used for
dependency injection in web search executors.
"""

from unittest.mock import Mock

import pytest
from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)

from unique_web_search.services.content_processing import WebPageChunk
from unique_web_search.services.executors.context import (
    ContentReducer,
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
    MessageLogCallback,
    QueryElicitationProtocol,
)
from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.utils import WebSearchDebugInfo


class TestExecutorServiceContext:
    """Tests for ExecutorServiceContext dataclass."""

    @pytest.mark.ai
    def test_init__stores_all_services__when_created(self) -> None:
        """
        Purpose: Verify ExecutorServiceContext stores all service dependencies.
        Why this matters: Services must be accessible for executor operations.
        Setup summary: Create context with all services, verify storage.
        """
        # Arrange
        mock_search_service = Mock()
        mock_crawler_service = Mock()
        mock_content_processor = Mock()
        mock_lm_service = Mock()
        mock_chunk_sorter = Mock()

        # Act
        context = ExecutorServiceContext(
            search_engine_service=mock_search_service,
            crawler_service=mock_crawler_service,
            content_processor=mock_content_processor,
            language_model_service=mock_lm_service,
            chunk_relevancy_sorter=mock_chunk_sorter,
        )

        # Assert
        assert context.search_engine_service == mock_search_service
        assert context.crawler_service == mock_crawler_service
        assert context.content_processor == mock_content_processor
        assert context.language_model_service == mock_lm_service
        assert context.chunk_relevancy_sorter == mock_chunk_sorter

    @pytest.mark.ai
    def test_init__accepts_none_chunk_relevancy_sorter__when_optional(self) -> None:
        """
        Purpose: Verify ExecutorServiceContext accepts None for optional chunk_relevancy_sorter.
        Why this matters: Chunk relevancy sorting is optional for some configurations.
        Setup summary: Create context with None sorter, verify it's stored.
        """
        # Arrange
        mock_search_service = Mock()
        mock_crawler_service = Mock()
        mock_content_processor = Mock()
        mock_lm_service = Mock()

        # Act
        context = ExecutorServiceContext(
            search_engine_service=mock_search_service,
            crawler_service=mock_crawler_service,
            content_processor=mock_content_processor,
            language_model_service=mock_lm_service,
            chunk_relevancy_sorter=None,
        )

        # Assert
        assert context.chunk_relevancy_sorter is None

    @pytest.mark.ai
    def test_init__is_dataclass__with_type_hints(self) -> None:
        """
        Purpose: Verify ExecutorServiceContext is a proper dataclass.
        Why this matters: Dataclass provides automatic initialization and representation.
        Setup summary: Check dataclass attributes exist.
        """
        # Arrange & Act
        mock_services = {
            "search_engine_service": Mock(),
            "crawler_service": Mock(),
            "content_processor": Mock(),
            "language_model_service": Mock(),
            "chunk_relevancy_sorter": Mock(),
        }
        context = ExecutorServiceContext(**mock_services)

        # Assert
        assert hasattr(context, "__dataclass_fields__")
        assert len(context.__dataclass_fields__) == 5


class TestExecutorConfiguration:
    """Tests for ExecutorConfiguration dataclass."""

    @pytest.mark.ai
    def test_init__stores_all_configuration_values__when_created(self) -> None:
        """
        Purpose: Verify ExecutorConfiguration stores all configuration parameters.
        Why this matters: Configuration values must be accessible for executor behavior.
        Setup summary: Create configuration with all values, verify storage.
        """
        # Arrange
        mock_lm = Mock()
        mock_sort_config = Mock(spec=ChunkRelevancySortConfig)
        company_id = "test-company-123"
        debug_info = WebSearchDebugInfo(parameters={"test": "value"})

        # Act
        config = ExecutorConfiguration(
            language_model=mock_lm,
            chunk_relevancy_sort_config=mock_sort_config,
            company_id=company_id,
            debug_info=debug_info,
        )

        # Assert
        assert config.language_model == mock_lm
        assert config.chunk_relevancy_sort_config == mock_sort_config
        assert config.company_id == company_id
        assert config.debug_info == debug_info

    @pytest.mark.ai
    def test_init__stores_company_id_as_string__when_provided(self) -> None:
        """
        Purpose: Verify ExecutorConfiguration stores company_id as string.
        Why this matters: Company ID is used for logging and feature flags.
        Setup summary: Create configuration with company ID, verify type and value.
        """
        # Arrange
        company_id = "company-abc-123"

        # Act
        config = ExecutorConfiguration(
            language_model=Mock(),
            chunk_relevancy_sort_config=Mock(),
            company_id=company_id,
            debug_info=WebSearchDebugInfo(parameters={}),
        )

        # Assert
        assert isinstance(config.company_id, str)
        assert config.company_id == "company-abc-123"

    @pytest.mark.ai
    def test_init__stores_debug_info_object__when_provided(self) -> None:
        """
        Purpose: Verify ExecutorConfiguration stores debug info correctly.
        Why this matters: Debug info tracks execution metrics and parameters.
        Setup summary: Create configuration with debug info, verify storage.
        """
        # Arrange
        debug_info = WebSearchDebugInfo(parameters={"mode": "v1", "queries": 3})

        # Act
        config = ExecutorConfiguration(
            language_model=Mock(),
            chunk_relevancy_sort_config=Mock(),
            company_id="test-company",
            debug_info=debug_info,
        )

        # Assert
        assert config.debug_info == debug_info
        assert config.debug_info.parameters == {"mode": "v1", "queries": 3}

    @pytest.mark.ai
    def test_init__is_dataclass__with_type_hints(self) -> None:
        """
        Purpose: Verify ExecutorConfiguration is a proper dataclass.
        Why this matters: Dataclass provides automatic initialization and representation.
        Setup summary: Check dataclass attributes exist.
        """
        # Arrange & Act
        config = ExecutorConfiguration(
            language_model=Mock(),
            chunk_relevancy_sort_config=Mock(),
            company_id="test",
            debug_info=WebSearchDebugInfo(parameters={}),
        )

        # Assert
        assert hasattr(config, "__dataclass_fields__")
        assert len(config.__dataclass_fields__) == 4


class TestExecutorCallbacks:
    """Tests for ExecutorCallbacks dataclass."""

    @pytest.mark.ai
    def test_init__stores_all_callbacks__when_created(self) -> None:
        """
        Purpose: Verify ExecutorCallbacks stores all callback functions.
        Why this matters: Callbacks must be accessible for executor operations.
        Setup summary: Create callbacks with all functions, verify storage.
        """
        # Arrange
        mock_message_log = Mock()
        mock_content_reducer = Mock()
        mock_query_elicitation = Mock()
        mock_progress_reporter = Mock()

        # Act
        callbacks = ExecutorCallbacks(
            message_log_callback=mock_message_log,
            content_reducer=mock_content_reducer,
            query_elicitation=mock_query_elicitation,
            tool_progress_reporter=mock_progress_reporter,
        )

        # Assert
        assert callbacks.message_log_callback == mock_message_log
        assert callbacks.content_reducer == mock_content_reducer
        assert callbacks.query_elicitation == mock_query_elicitation
        assert callbacks.tool_progress_reporter == mock_progress_reporter

    @pytest.mark.ai
    def test_init__accepts_none_tool_progress_reporter__when_optional(self) -> None:
        """
        Purpose: Verify ExecutorCallbacks accepts None for optional tool_progress_reporter.
        Why this matters: Progress reporter is optional in some execution contexts.
        Setup summary: Create callbacks without reporter, verify None is stored.
        """
        # Arrange
        mock_message_log = Mock()
        mock_content_reducer = Mock()
        mock_query_elicitation = Mock()

        # Act
        callbacks = ExecutorCallbacks(
            message_log_callback=mock_message_log,
            content_reducer=mock_content_reducer,
            query_elicitation=mock_query_elicitation,
            tool_progress_reporter=None,
        )

        # Assert
        assert callbacks.tool_progress_reporter is None

    @pytest.mark.ai
    def test_init__defaults_tool_progress_reporter_to_none__when_omitted(self) -> None:
        """
        Purpose: Verify ExecutorCallbacks defaults tool_progress_reporter to None.
        Why this matters: Optional parameter should have sensible default.
        Setup summary: Create callbacks without specifying reporter, verify None.
        """
        # Arrange
        mock_message_log = Mock()
        mock_content_reducer = Mock()
        mock_query_elicitation = Mock()

        # Act
        callbacks = ExecutorCallbacks(
            message_log_callback=mock_message_log,
            content_reducer=mock_content_reducer,
            query_elicitation=mock_query_elicitation,
        )

        # Assert
        assert callbacks.tool_progress_reporter is None

    @pytest.mark.ai
    def test_init__is_dataclass__with_type_hints(self) -> None:
        """
        Purpose: Verify ExecutorCallbacks is a proper dataclass.
        Why this matters: Dataclass provides automatic initialization and representation.
        Setup summary: Check dataclass attributes exist.
        """
        # Arrange & Act
        callbacks = ExecutorCallbacks(
            message_log_callback=Mock(),
            content_reducer=Mock(),
            query_elicitation=Mock(),
        )

        # Assert
        assert hasattr(callbacks, "__dataclass_fields__")
        assert len(callbacks.__dataclass_fields__) == 4


class TestContentReducerProtocol:
    """Tests for ContentReducer protocol."""

    @pytest.mark.ai
    def test_protocol__accepts_callable__with_correct_signature(self) -> None:
        """
        Purpose: Verify ContentReducer protocol accepts callables with correct signature.
        Why this matters: Protocol ensures type safety for content reducer functions.
        Setup summary: Create function matching protocol, verify it's accepted.
        """

        # Arrange
        def reducer(chunks: list[WebPageChunk]) -> list[WebPageChunk]:
            return chunks[:10]

        # Act & Assert - should not raise type error
        callback: ContentReducer = reducer
        assert callable(callback)

    @pytest.mark.ai
    def test_protocol__accepts_lambda__with_correct_signature(self) -> None:
        """
        Purpose: Verify ContentReducer protocol accepts lambdas with correct signature.
        Why this matters: Lambdas are common for simple reducer implementations.
        Setup summary: Create lambda matching protocol, verify it's accepted.
        """

        # Arrange & Act
        def reducer(chunks: list[WebPageChunk]) -> list[WebPageChunk]:
            return chunks[:5]

        # Assert
        assert callable(reducer)
        mock_chunks = [Mock(spec=WebPageChunk) for _ in range(10)]
        result = reducer(mock_chunks)
        assert len(result) == 5

    @pytest.mark.ai
    def test_protocol__accepts_mock__with_correct_behavior(self) -> None:
        """
        Purpose: Verify ContentReducer protocol works with mocks in tests.
        Why this matters: Mocks are essential for testing executor behavior.
        Setup summary: Create mock matching protocol, verify it's callable.
        """
        # Arrange
        mock_reducer = Mock(spec=ContentReducer)
        mock_reducer.return_value = []

        # Act
        result = mock_reducer([Mock(spec=WebPageChunk)])

        # Assert
        assert callable(mock_reducer)
        mock_reducer.assert_called_once()
        assert result == []


class TestMessageLogCallbackProtocol:
    """Tests for MessageLogCallback protocol."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_protocol__has_log_progress_method__with_correct_signature(
        self,
    ) -> None:
        """
        Purpose: Verify MessageLogCallback protocol includes log_progress method.
        Why this matters: Protocol ensures message log callbacks support progress logging.
        Setup summary: Create mock with protocol methods, verify log_progress works.
        """
        # Arrange
        from unittest.mock import AsyncMock

        mock_callback = Mock(spec=MessageLogCallback)
        mock_callback.log_progress = AsyncMock()

        # Act
        await mock_callback.log_progress("Test progress")

        # Assert
        mock_callback.log_progress.assert_called_once_with("Test progress")

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_protocol__has_log_queries_method__with_correct_signature(
        self,
    ) -> None:
        """
        Purpose: Verify MessageLogCallback protocol includes log_queries method.
        Why this matters: Protocol ensures message log callbacks support query logging.
        Setup summary: Create mock with protocol methods, verify log_queries works.
        """
        # Arrange
        from unittest.mock import AsyncMock

        mock_callback = Mock(spec=MessageLogCallback)
        mock_callback.log_queries = AsyncMock()

        # Act
        await mock_callback.log_queries(["query1", "query2"])

        # Assert
        mock_callback.log_queries.assert_called_once_with(["query1", "query2"])

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_protocol__has_log_web_search_results_method__with_correct_signature(
        self,
    ) -> None:
        """
        Purpose: Verify MessageLogCallback protocol includes log_web_search_results method.
        Why this matters: Protocol ensures message log callbacks support result logging.
        Setup summary: Create mock with protocol methods, verify log_web_search_results works.
        """
        # Arrange
        from unittest.mock import AsyncMock

        mock_callback = Mock(spec=MessageLogCallback)
        mock_callback.log_web_search_results = AsyncMock()
        mock_results = [Mock(spec=WebSearchResult)]

        # Act
        await mock_callback.log_web_search_results(mock_results)

        # Assert
        mock_callback.log_web_search_results.assert_called_once_with(mock_results)


class TestQueryElicitationProtocol:
    """Tests for QueryElicitationProtocol."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_protocol__accepts_async_callable__with_correct_signature(
        self,
    ) -> None:
        """
        Purpose: Verify QueryElicitationProtocol accepts async callables.
        Why this matters: Query elicitation is async operation requiring user interaction.
        Setup summary: Create async function matching protocol, verify it's accepted.
        """

        # Arrange
        async def elicitation(queries: list[str]) -> list[str]:
            return queries

        # Act
        callback: QueryElicitationProtocol = elicitation
        result = await callback(["test query"])

        # Assert
        assert result == ["test query"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_protocol__accepts_async_mock__with_correct_behavior(self) -> None:
        """
        Purpose: Verify QueryElicitationProtocol works with async mocks in tests.
        Why this matters: Async mocks are essential for testing executor behavior.
        Setup summary: Create async mock matching protocol, verify it's callable.
        """
        # Arrange
        from unittest.mock import AsyncMock

        mock_elicitation = AsyncMock(spec=QueryElicitationProtocol)
        mock_elicitation.return_value = ["elicitated query"]

        # Act
        result = await mock_elicitation(["original query"])

        # Assert
        mock_elicitation.assert_called_once_with(["original query"])
        assert result == ["elicitated query"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_protocol__transforms_queries__when_called(self) -> None:
        """
        Purpose: Verify QueryElicitationProtocol can transform input queries.
        Why this matters: Elicitation may refine or expand queries based on context.
        Setup summary: Create function that modifies queries, verify transformation.
        """

        # Arrange
        async def elicitation(queries: list[str]) -> list[str]:
            return [f"refined: {q}" for q in queries]

        # Act
        callback: QueryElicitationProtocol = elicitation
        result = await callback(["query1", "query2"])

        # Assert
        assert result == ["refined: query1", "refined: query2"]


class TestContextIntegration:
    """Integration tests for context classes working together."""

    @pytest.mark.ai
    def test_context_classes__work_together__in_executor_initialization(self) -> None:
        """
        Purpose: Verify all context classes work together for executor initialization.
        Why this matters: Context classes reduce parameter redundancy in executors.
        Setup summary: Create all contexts, verify they can be used together.
        """
        # Arrange
        services = ExecutorServiceContext(
            search_engine_service=Mock(),
            crawler_service=Mock(),
            content_processor=Mock(),
            language_model_service=Mock(),
            chunk_relevancy_sorter=Mock(),
        )

        config = ExecutorConfiguration(
            language_model=Mock(),
            chunk_relevancy_sort_config=Mock(),
            company_id="test-company",
            debug_info=WebSearchDebugInfo(parameters={}),
        )

        callbacks = ExecutorCallbacks(
            message_log_callback=Mock(),
            content_reducer=Mock(),
            query_elicitation=Mock(),
            tool_progress_reporter=Mock(),
        )

        # Act & Assert - should work without errors
        assert services is not None
        assert config is not None
        assert callbacks is not None
        assert config.company_id == "test-company"

    @pytest.mark.ai
    def test_context_classes__support_optional_fields__when_not_needed(self) -> None:
        """
        Purpose: Verify context classes handle optional fields correctly.
        Why this matters: Not all features are needed in every execution context.
        Setup summary: Create contexts with optional fields as None, verify behavior.
        """
        # Arrange & Act
        services = ExecutorServiceContext(
            search_engine_service=Mock(),
            crawler_service=Mock(),
            content_processor=Mock(),
            language_model_service=Mock(),
            chunk_relevancy_sorter=None,  # Optional
        )

        callbacks = ExecutorCallbacks(
            message_log_callback=Mock(),
            content_reducer=Mock(),
            query_elicitation=Mock(),
            # tool_progress_reporter omitted (optional)
        )

        # Assert
        assert services.chunk_relevancy_sorter is None
        assert callbacks.tool_progress_reporter is None
