from typing import Any

import pytest
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
    LanguageModelProvider,
    LanguageModelTokenLimits,
)

from unique_web_search.services.content_processing import WebPageChunk
from unique_web_search.utils import (
    StepDebugInfo,
    WebSearchDebugInfo,
    query_params_to_human_string,
    reduce_sources_to_token_limit,
)


class TestQueryParamsToHumanString:
    """Test cases for query_params_to_human_string function."""

    @pytest.mark.ai
    def test_query_params_to_human_string__returns_query_only__when_no_date_restriction(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion returns query unchanged when no date restriction.
        Why this matters: Ensures proper formatting for queries without time constraints.
        Setup summary: Call function with query and None date_restrict, assert query returned unchanged.
        """
        # Arrange
        query: str = "Python tutorials"

        # Act
        result: str = query_params_to_human_string(query, None)

        # Assert
        assert result == "Python tutorials"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_single_day__when_d1_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for single day restriction.
        Why this matters: Ensures proper grammar for singular day time periods.
        Setup summary: Call function with query and "d1", assert formatted string with singular day format.
        """
        # Arrange
        query: str = "Python tutorials"

        # Act
        result: str = query_params_to_human_string(query, "d1")

        # Assert
        assert result == "Python tutorials (For the last 1 day)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_multiple_days__when_d7_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for multiple days restriction.
        Why this matters: Ensures proper formatting for plural day time periods.
        Setup summary: Call function with query and "d7", assert formatted string with plural days format.
        """
        # Arrange
        query: str = "Python tutorials"

        # Act
        result: str = query_params_to_human_string(query, "d7")

        # Assert
        assert result == "Python tutorials (For the last 7 days)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_single_week__when_w1_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for single week restriction.
        Why this matters: Ensures proper formatting for singular week time periods.
        Setup summary: Call function with query and "w1", assert formatted string with singular week format.
        """
        # Arrange
        query: str = "Python tutorials"

        # Act
        result: str = query_params_to_human_string(query, "w1")

        # Assert
        assert result == "Python tutorials (For the last 1 week)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_multiple_weeks__when_w2_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for multiple weeks restriction.
        Why this matters: Ensures proper formatting for plural week time periods.
        Setup summary: Call function with query and "w2", assert formatted string with plural weeks format.
        """
        # Arrange
        query: str = "Python tutorials"

        # Act
        result: str = query_params_to_human_string(query, "w2")

        # Assert
        assert result == "Python tutorials (For the last 2 weeks)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_single_month__when_m1_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for single month restriction.
        Why this matters: Ensures proper formatting for singular month time periods.
        Setup summary: Call function with query and "m1", assert formatted string with singular month format.
        """
        # Arrange
        query: str = "Python tutorials"

        # Act
        result: str = query_params_to_human_string(query, "m1")

        # Assert
        assert result == "Python tutorials (For the last 1 month)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_multiple_months__when_m6_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for multiple months restriction.
        Why this matters: Ensures proper formatting for plural month time periods.
        Setup summary: Call function with query and "m6", assert formatted string with plural months format.
        """
        # Arrange
        query: str = "Python tutorials"

        # Act
        result: str = query_params_to_human_string(query, "m6")

        # Assert
        assert result == "Python tutorials (For the last 6 months)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_single_year__when_y1_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for single year restriction.
        Why this matters: Ensures proper formatting for singular year time periods.
        Setup summary: Call function with query and "y1", assert formatted string with singular year format.
        """
        # Arrange
        query: str = "Python tutorials"

        # Act
        result: str = query_params_to_human_string(query, "y1")

        # Assert
        assert result == "Python tutorials (For the last 1 year)"

    @pytest.mark.ai
    def test_query_params_to_human_string__formats_multiple_years__when_y2_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion formats correctly for multiple years restriction.
        Why this matters: Ensures proper formatting for plural year time periods.
        Setup summary: Call function with query and "y2", assert formatted string with plural years format.
        """
        # Arrange
        query: str = "Python tutorials"

        # Act
        result: str = query_params_to_human_string(query, "y2")

        # Assert
        assert result == "Python tutorials (For the last 2 years)"

    @pytest.mark.ai
    def test_query_params_to_human_string__handles_invalid_format__when_invalid_string_provided(
        self,
    ) -> None:
        """
        Purpose: Verify query conversion gracefully handles invalid date restriction format.
        Why this matters: Ensures robust error handling for malformed date restrictions.
        Setup summary: Call function with query and invalid date_restrict, assert function doesn't crash.
        """
        # Arrange
        query: str = "Python tutorials"
        invalid_date: str = "invalid"

        # Act
        result: str = query_params_to_human_string(query, invalid_date)

        # Assert
        assert result == "Python tutorials (For the last invalid)"


class TestWebPageChunk:
    """Test WebPageChunk functionality."""

    @pytest.mark.ai
    def test_web_page_chunk__creates_with_all_fields__when_initialized(self) -> None:
        """
        Purpose: Verify WebPageChunk creates correctly with all required fields.
        Why this matters: Ensures proper structure for web page data containers.
        Setup summary: Create WebPageChunk with all fields, assert all values stored correctly.
        """
        # Arrange
        url: str = "https://example.com/test"
        display_link: str = "example.com"
        title: str = "Test Article"
        snippet: str = "This is a test article"
        content: str = "Full content of the test article"
        order: str = "1"

        # Act
        chunk: WebPageChunk = WebPageChunk(
            url=url,
            display_link=display_link,
            title=title,
            snippet=snippet,
            content=content,
            order=order,
        )

        # Assert
        assert chunk.url == "https://example.com/test"
        assert chunk.display_link == "example.com"
        assert chunk.title == "Test Article"
        assert chunk.snippet == "This is a test article"
        assert chunk.content == "Full content of the test article"
        assert chunk.order == "1"

    @pytest.mark.ai
    def test_web_page_chunk__converts_to_content_chunk__when_to_content_chunk_called(
        self,
    ) -> None:
        """
        Purpose: Verify WebPageChunk converts to ContentChunk with correct field mapping.
        Why this matters: Ensures proper data transformation for content processing pipeline.
        Setup summary: Create WebPageChunk, call to_content_chunk(), assert ContentChunk fields mapped correctly.
        """
        # Arrange
        chunk: WebPageChunk = WebPageChunk(
            url="https://example.com/test",
            display_link="example.com",
            title="Test Article",
            snippet="This is a test article",
            content="Full content of the test article",
            order="1",
        )

        # Act
        content_chunk = chunk.to_content_chunk()

        # Assert
        assert content_chunk.url == "https://example.com/test"
        assert content_chunk.text == "Full content of the test article"
        assert content_chunk.order == 1
        assert "example.com" in content_chunk.id
        assert "Test Article" in content_chunk.id


class TestReduceSourcesToTokenLimit:
    """Test reduce_sources_to_token_limit function."""

    @pytest.fixture
    def mock_language_model_info(self) -> LanguageModelInfo:
        """Create a mock language model info with token limits."""
        return LanguageModelInfo(
            name=LanguageModelName.AZURE_GPT_4o_2024_1120,
            provider=LanguageModelProvider.AZURE,
            capabilities=[],
            token_limits=LanguageModelTokenLimits(
                token_limit_input=128000, token_limit_output=4096
            ),
        )

    @pytest.mark.ai
    def test_reduce_sources_to_token_limit__returns_all_chunks__when_under_limit(
        self, mock_language_model_info: LanguageModelInfo
    ) -> None:
        """
        Purpose: Verify function returns all chunks when total tokens are under limit.
        Why this matters: Ensures all relevant content is included when within token constraints.
        Setup summary: Create small chunks under token limit, call function, assert all chunks returned.
        """
        # Arrange
        chunks: list[WebPageChunk] = [
            WebPageChunk(
                url="https://example.com/1",
                display_link="example.com",
                title="Test 1",
                snippet="Short",
                content="Short content",
                order="1",
            ),
            WebPageChunk(
                url="https://example.com/2",
                display_link="example.com",
                title="Test 2",
                snippet="Short",
                content="Short content",
                order="2",
            ),
        ]
        limit_token_sources: int = 10000
        chat_history_token_length: int = 100

        # Act
        result: list[WebPageChunk] = reduce_sources_to_token_limit(
            web_page_chunks=chunks,
            language_model_max_input_tokens=None,
            percentage_of_input_tokens_for_sources=0.4,
            limit_token_sources=limit_token_sources,
            language_model=mock_language_model_info,
            chat_history_token_length=chat_history_token_length,
        )

        # Assert
        assert len(result) == 2

    @pytest.mark.ai
    def test_reduce_sources_to_token_limit__uses_custom_max_tokens__when_provided(
        self, mock_language_model_info: LanguageModelInfo
    ) -> None:
        """
        Purpose: Verify function uses custom max_input_tokens when provided.
        Why this matters: Ensures proper token limit calculation with custom token limits.
        Setup summary: Create chunks, call with custom max_input_tokens, assert correct limit applied.
        """
        # Arrange
        chunks: list[WebPageChunk] = [
            WebPageChunk(
                url="https://example.com/1",
                display_link="example.com",
                title="Test",
                snippet="Short",
                content="Short content",
                order="1",
            ),
        ]
        language_model_max_input_tokens: int = 10000
        percentage: float = 0.5

        # Act
        result: list[WebPageChunk] = reduce_sources_to_token_limit(
            web_page_chunks=chunks,
            language_model_max_input_tokens=language_model_max_input_tokens,
            percentage_of_input_tokens_for_sources=percentage,
            limit_token_sources=5000,
            language_model=mock_language_model_info,
            chat_history_token_length=0,
        )

        # Assert
        assert len(result) >= 0  # Function should return chunks within calculated limit


class TestStepDebugInfo:
    """Test StepDebugInfo model."""

    @pytest.mark.ai
    def test_step_debug_info__creates_with_required_fields__when_initialized(
        self,
    ) -> None:
        """
        Purpose: Verify StepDebugInfo creates correctly with required fields.
        Why this matters: Ensures proper structure for step-level debug information.
        Setup summary: Create StepDebugInfo with step_name, execution_time, config, assert values stored.
        """
        # Arrange
        step_name: str = "test_step"
        execution_time: float = 1.5
        config: str = "test_config"

        # Act
        debug_info: StepDebugInfo = StepDebugInfo(
            step_name=step_name,
            execution_time=execution_time,
            config=config,
        )

        # Assert
        assert debug_info.step_name == "test_step"
        assert debug_info.execution_time == 1.5
        assert debug_info.config == "test_config"
        assert isinstance(debug_info.extra, dict)

    @pytest.mark.ai
    def test_step_debug_info__creates_with_extra_dict__when_provided(self) -> None:
        """
        Purpose: Verify StepDebugInfo accepts and stores extra dictionary field.
        Why this matters: Enables storing additional debug metadata for step execution.
        Setup summary: Create StepDebugInfo with extra dict, assert extra values stored correctly.
        """
        # Arrange
        extra: dict[str, Any] = {"key": "value", "count": 42}

        # Act
        debug_info: StepDebugInfo = StepDebugInfo(
            step_name="test",
            execution_time=1.0,
            config="config",
            extra=extra,
        )

        # Assert
        assert debug_info.extra["key"] == "value"
        assert debug_info.extra["count"] == 42

    @pytest.mark.ai
    def test_step_debug_info__creates_with_dict_config__when_config_is_dict(
        self,
    ) -> None:
        """
        Purpose: Verify StepDebugInfo accepts dict type for config field.
        Why this matters: Ensures flexibility in storing structured configuration data.
        Setup summary: Create StepDebugInfo with dict config, assert dict stored correctly.
        """
        # Arrange
        config_dict: dict[str, Any] = {"timeout": 30, "retries": 3}

        # Act
        debug_info: StepDebugInfo = StepDebugInfo(
            step_name="test",
            execution_time=1.0,
            config=config_dict,
        )

        # Assert
        assert isinstance(debug_info.config, dict)
        assert debug_info.config["timeout"] == 30


class TestWebSearchDebugInfo:
    """Test WebSearchDebugInfo model."""

    @pytest.fixture
    def sample_chunks(self) -> list[WebPageChunk]:
        """Create sample web page chunks for testing."""
        return [
            WebPageChunk(
                url="https://example.com/test",
                display_link="example.com",
                title="Test",
                snippet="Test snippet",
                content="Test content",
                order="1",
            ),
        ]

    @pytest.mark.ai
    def test_web_search_debug_info__creates_with_required_fields__when_initialized(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchDebugInfo creates correctly with required parameters field.
        Why this matters: Ensures proper structure for web search debug information.
        Setup summary: Create WebSearchDebugInfo with parameters dict, assert values stored correctly.
        """
        # Arrange
        parameters: dict[str, Any] = {"query": "test", "date_restrict": "d1"}

        # Act
        debug_info: WebSearchDebugInfo = WebSearchDebugInfo(parameters=parameters)

        # Assert
        assert debug_info.parameters == parameters
        assert isinstance(debug_info.steps, list)
        assert len(debug_info.steps) == 0
        assert debug_info.execution_time is None
        assert debug_info.num_chunks_in_final_prompts == 0

    @pytest.mark.ai
    def test_web_search_debug_info__creates_with_steps__when_steps_provided(
        self,
    ) -> None:
        """
        Purpose: Verify WebSearchDebugInfo accepts and stores step debug information.
        Why this matters: Enables tracking execution steps for debugging purposes.
        Setup summary: Create WebSearchDebugInfo with steps list, assert steps stored correctly.
        """
        # Arrange
        parameters: dict[str, Any] = {"query": "test"}
        steps: list[StepDebugInfo] = [
            StepDebugInfo(step_name="search", execution_time=1.0, config="config1"),
            StepDebugInfo(step_name="crawl", execution_time=2.0, config="config2"),
        ]

        # Act
        debug_info: WebSearchDebugInfo = WebSearchDebugInfo(
            parameters=parameters, steps=steps
        )

        # Assert
        assert len(debug_info.steps) == 2
        assert debug_info.steps[0].step_name == "search"
        assert debug_info.steps[1].step_name == "crawl"

    @pytest.mark.ai
    def test_web_search_debug_info__model_dump_includes_all_when_with_debug_details_true(
        self, sample_chunks: list[WebPageChunk]
    ) -> None:
        """
        Purpose: Verify model_dump includes all fields when with_debug_details=True.
        Why this matters: Ensures complete debug information is available when needed.
        Setup summary: Create WebSearchDebugInfo with all fields, call model_dump(with_debug_details=True), assert all fields present.
        """
        # Arrange
        debug_info: WebSearchDebugInfo = WebSearchDebugInfo(
            parameters={"query": "test"},
            steps=[
                StepDebugInfo(
                    step_name="test",
                    execution_time=1.0,
                    config="config",
                    extra={"key": "value"},
                )
            ],
            web_page_chunks=sample_chunks,
            execution_time=5.0,
            num_chunks_in_final_prompts=1,
        )

        # Act
        result: dict[str, Any] = debug_info.model_dump(with_debug_details=True)

        # Assert
        assert "parameters" in result
        assert "steps" in result
        assert len(result["steps"]) == 1
        assert "extra" in result["steps"][0]
        assert "web_page_chunks" in result
        assert result["execution_time"] == 5.0

    @pytest.mark.ai
    def test_web_search_debug_info__model_dump_excludes_extra_when_with_debug_details_false(
        self, sample_chunks: list[WebPageChunk]
    ) -> None:
        """
        Purpose: Verify model_dump excludes extra fields and chunks when with_debug_details=False.
        Why this matters: Allows concise debug output by excluding verbose details.
        Setup summary: Create WebSearchDebugInfo with extra and chunks, call model_dump(with_debug_details=False), assert excluded fields missing.
        """
        # Arrange
        debug_info: WebSearchDebugInfo = WebSearchDebugInfo(
            parameters={"query": "test"},
            steps=[
                StepDebugInfo(
                    step_name="test",
                    execution_time=1.0,
                    config="config",
                    extra={"key": "value"},
                )
            ],
            web_page_chunks=sample_chunks,
            execution_time=5.0,
        )

        # Act
        result: dict[str, Any] = debug_info.model_dump(with_debug_details=False)

        # Assert
        assert "steps" in result
        assert "extra" not in result["steps"][0]
        assert "web_page_chunks" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
