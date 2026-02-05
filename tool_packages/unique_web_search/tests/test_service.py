from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from unique_web_search.schema import WebSearchPlan, WebSearchToolParameters
from unique_web_search.service import WebSearchTool


class TestWebSearchToolDescription:
    """Test WebSearchTool.tool_description() method."""

    @pytest.mark.ai
    def test_tool_description__returns_v1_parameters__when_mode_is_v1(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify tool_description returns WebSearchToolParameters for V1 mode.
        Why this matters: Ensures correct parameter schema is used for V1 mode.
        Setup summary: Mock WebSearchTool with V1 config, patch dependencies.
        """
        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1
        tool.tool_parameter_calls = None  # type: ignore

        result = tool.tool_description()

        assert hasattr(result, "name")
        assert result.name == "WebSearch"
        assert hasattr(result, "description")
        assert result.description == "V1 tool description"
        assert issubclass(tool.tool_parameter_calls, WebSearchToolParameters)

    @pytest.mark.ai
    def test_tool_description__returns_v2_plan__when_mode_is_v2(
        self,
        mock_web_search_config_v2: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify tool_description returns WebSearchPlan for V2 mode.
        Why this matters: Ensures correct parameter schema is used for V2 mode.
        Setup summary: Mock WebSearchTool with V2 config, patch dependencies.
        """
        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v2
        tool.tool_parameter_calls = None  # type: ignore

        result = tool.tool_description()

        assert hasattr(result, "name")
        assert result.name == "WebSearch"
        assert hasattr(result, "description")
        assert result.description == "V2 tool description"
        assert tool.tool_parameter_calls == WebSearchPlan


class TestWebSearchToolDescriptionForSystemPrompt:
    """Test WebSearchTool.tool_description_for_system_prompt() method."""

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__returns_unchanged__when_mode_is_v1(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify tool_description_for_system_prompt returns unchanged string for V1.
        Why this matters: V1 mode doesn't require placeholder replacement.
        Setup summary: Mock WebSearchTool with V1 config.
        """
        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1

        result: str = tool.tool_description_for_system_prompt()

        assert isinstance(result, str)
        assert result == "V1 system prompt"

    @pytest.mark.ai
    def test_tool_description_for_system_prompt__replaces_max_steps__when_mode_is_v2(
        self,
        mock_web_search_config_v2: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify tool_description_for_system_prompt replaces $max_steps placeholder for V2.
        Why this matters: V2 mode requires dynamic max_steps value in system prompt.
        Setup summary: Mock WebSearchTool with V2 config containing $max_steps placeholder.
        """
        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v2

        result: str = tool.tool_description_for_system_prompt()

        assert isinstance(result, str)
        assert result == "V2 system prompt with 5"


class TestWebSearchToolFormatInformation:
    """Test WebSearchTool.tool_format_information_for_system_prompt() method."""

    @pytest.mark.ai
    def test_tool_format_information_for_system_prompt__returns_config_value(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify tool_format_information_for_system_prompt returns config value.
        Why this matters: Ensures format information is correctly retrieved from config.
        Setup summary: Mock WebSearchTool with config containing format information.
        """
        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1

        result: str = tool.tool_format_information_for_system_prompt()

        assert isinstance(result, str)
        assert result == "Test format info"


class TestWebSearchToolEvaluationCheckList:
    """Test WebSearchTool.evaluation_check_list() method."""

    @pytest.mark.ai
    def test_evaluation_check_list__returns_config_value(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify evaluation_check_list returns config value.
        Why this matters: Ensures evaluation checks are correctly retrieved from config.
        Setup summary: Mock WebSearchTool with config containing evaluation check list.
        """
        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1

        result: list = tool.evaluation_check_list()

        assert isinstance(result, list)
        assert result == []


class TestWebSearchToolGetExecutor:
    """Test WebSearchTool._get_executor() method."""

    @pytest.mark.ai
    def test_get_executor__returns_v2_executor__when_parameters_is_web_search_plan(
        self,
        mock_web_search_config_v2: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify _get_executor returns WebSearchV2Executor for WebSearchPlan parameters.
        Why this matters: Ensures correct executor is selected for V2 mode.
        Setup summary: Mock WebSearchTool with V2 config and WebSearchPlan parameters.
        """
        from unique_web_search.services.executors.web_search_v2_executor import (
            WebSearchV2Executor,
        )

        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        
        # Mock QueryElicitationService
        mock_elicitation_service = Mock()
        mocker.patch(
            "unique_web_search.service.QueryElicitationService",
            return_value=mock_elicitation_service,
        )
        
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v2
        tool.search_engine_service = Mock()
        tool._language_model_service = Mock()
        tool.language_model = Mock()
        tool.crawler_service = Mock()
        tool.company_id = "test-company"
        tool.content_processor = Mock()
        tool.chunk_relevancy_sorter = Mock()
        tool.content_reducer = Mock()
        tool._tool_progress_reporter = None
        tool._chat_service = Mock()
        tool._display_name = "Web Search"
        tool.settings = Mock()
        tool.settings.display_name = "Web Search"

        tool_call = Mock()
        parameters = WebSearchPlan(
            objective="test", query_analysis="test", steps=[], expected_outcome="test"
        )
        debug_info = Mock()
        web_search_message_logger = Mock()

        result = tool._get_executor(tool_call, parameters, debug_info, web_search_message_logger)

        assert isinstance(result, WebSearchV2Executor)

    @pytest.mark.ai
    def test_get_executor__returns_v1_executor__when_parameters_is_web_search_tool_parameters(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify _get_executor returns WebSearchV1Executor for WebSearchToolParameters.
        Why this matters: Ensures correct executor is selected for V1 mode.
        Setup summary: Mock WebSearchTool with V1 config and WebSearchToolParameters.
        """
        from unique_web_search.services.executors.web_search_v1_executor import (
            WebSearchV1Executor,
        )

        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        
        # Mock QueryElicitationService
        mock_elicitation_service = Mock()
        mocker.patch(
            "unique_web_search.service.QueryElicitationService",
            return_value=mock_elicitation_service,
        )
        
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1
        tool.search_engine_service = Mock()
        tool._language_model_service = Mock()
        tool.language_model = Mock()
        tool.crawler_service = Mock()
        tool.company_id = "test-company"
        tool.content_processor = Mock()
        tool.chunk_relevancy_sorter = Mock()
        tool.content_reducer = Mock()
        tool._tool_progress_reporter = None
        tool._chat_service = Mock()
        tool._display_name = "Web Search"
        tool.settings = Mock()
        tool.settings.display_name = "Web Search"
        tool._chat_service = Mock()

        tool_call = Mock()
        parameters = WebSearchToolParameters(query="test", date_restrict=None)
        debug_info = Mock()
        web_search_message_logger = Mock()

        result = tool._get_executor(tool_call, parameters, debug_info, web_search_message_logger)

        assert isinstance(result, WebSearchV1Executor)

    @pytest.mark.ai
    def test_get_executor__raises_value_error__when_parameters_is_invalid(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify _get_executor raises ValueError for invalid parameters type.
        Why this matters: Ensures type safety and proper error handling.
        Setup summary: Mock WebSearchTool with invalid parameters type.
        """
        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        
        # Mock QueryElicitationService
        mock_elicitation_service = Mock()
        mocker.patch(
            "unique_web_search.service.QueryElicitationService",
            return_value=mock_elicitation_service,
        )
        
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1
        tool._chat_service = Mock()
        tool._display_name = "Web Search"
        tool.settings = Mock()
        tool.settings.display_name = "Web Search"
        tool.search_engine_service = Mock()
        tool._language_model_service = Mock()
        tool.language_model = Mock()
        tool.crawler_service = Mock()
        tool.company_id = "test-company"
        tool.content_processor = Mock()
        tool.chunk_relevancy_sorter = Mock()
        tool.content_reducer = Mock()
        tool._tool_progress_reporter = None

        tool_call = Mock()
        parameters = "invalid"  # type: ignore
        debug_info = Mock()
        web_search_message_logger = Mock()

        with pytest.raises(ValueError) as exc_info:
            tool._get_executor(tool_call, parameters, debug_info, web_search_message_logger)  # type: ignore

        assert isinstance(exc_info.value, ValueError)
        assert "Invalid parameters" in str(exc_info.value)


class TestWebSearchToolPrepareMessageLogsEntries:
    """Test WebSearchTool._prepare_message_logs_entries() method.
    
    NOTE: This test class is deprecated as WebSearchLogEntry has been removed.
    The message_log service now handles logging directly.
    """

    @pytest.mark.ai
    def test_prepare_message_logs_entries__deprecated(
        self,
        mocker: Any,
    ) -> None:
        """
        Purpose: This test is deprecated as WebSearchLogEntry has been removed.
        Why this matters: The message_log service now handles logging directly.
        Setup summary: Placeholder for deprecated functionality.
        """
        # This test is deprecated and should be removed or refactored
        # The WebSearchLogEntry class no longer exists
        # Message logging is now handled by WebSearchMessageLogger
        pass


class TestWebSearchToolGetEvaluationChecksBasedOnToolResponse:
    """Test WebSearchTool.get_evaluation_checks_based_on_tool_response() method."""

    @pytest.mark.ai
    def test_get_evaluation_checks_based_on_tool_response__returns_empty_list__when_content_chunks_is_empty(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify get_evaluation_checks_based_on_tool_response returns empty list when no content chunks.
        Why this matters: No evaluation needed when tool returns no content.
        Setup summary: Mock WebSearchTool and create ToolCallResponse with empty content_chunks.
        """
        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1

        tool_response = Mock()
        tool_response.content_chunks = []

        result: list = tool.get_evaluation_checks_based_on_tool_response(tool_response)

        assert isinstance(result, list)
        assert result == []

    @pytest.mark.ai
    def test_get_evaluation_checks_based_on_tool_response__returns_evaluation_check_list__when_content_chunks_exists(
        self,
        mock_web_search_config_v1: Mock,
        sample_content_chunks: list,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify get_evaluation_checks_based_on_tool_response returns evaluation check list when content exists.
        Why this matters: Evaluation checks should be returned when tool produces content.
        Setup summary: Mock WebSearchTool and create ToolCallResponse with content chunks.
        """
        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")
        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1

        tool_response = Mock()
        tool_response.content_chunks = sample_content_chunks

        result: list = tool.get_evaluation_checks_based_on_tool_response(tool_response)

        assert isinstance(result, list)
        assert result == []


class TestWebSearchToolRun:
    """Test WebSearchTool.run() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__returns_tool_call_response__when_executor_succeeds(
        self,
        mock_web_search_config_v1: Mock,
        sample_web_search_tool_parameters: WebSearchToolParameters,
        sample_content_chunks: list,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify run returns successful ToolCallResponse when executor completes successfully.
        Why this matters: Ensures successful execution path works correctly.
        Setup summary: Mock WebSearchTool, executor, and all dependencies.
        """
        mock_executor = AsyncMock()
        mock_executor.run = AsyncMock(
            return_value=sample_content_chunks
        )
        mock_executor.notify_name = "test-name"
        mock_executor.notify_message = "test-message"

        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")

        # Mock WebSearchDebugInfo to return a proper dict from model_dump
        mock_debug_info_class = Mock()
        mock_debug_info_instance = Mock()
        mock_debug_info_instance.model_dump.return_value = {"test": "debug_info"}
        mock_debug_info_instance.num_chunks_in_final_prompts = None
        mock_debug_info_instance.execution_time = None
        mock_debug_info_class.return_value = mock_debug_info_instance
        mocker.patch(
            "unique_web_search.service.WebSearchDebugInfo", mock_debug_info_class
        )
        
        # Mock WebSearchMessageLogger
        mock_message_logger = Mock()
        mock_message_logger.finished = AsyncMock()
        mocker.patch(
            "unique_web_search.service.WebSearchMessageLogger",
            return_value=mock_message_logger,
        )

        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )
        mocker.patch.object(WebSearchTool, "_get_executor", return_value=mock_executor)

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1
        tool.tool_parameter_calls = WebSearchToolParameters
        tool.logger = Mock()
        tool._message_step_logger = Mock()
        tool._tool_progress_reporter = None
        tool._display_name = "WebSearch"
        tool.company_id = "test-company"
        tool.debug = False
        tool.name = "WebSearch"
        tool.settings = Mock()
        tool.settings.display_name = "WebSearch"

        tool_call = Mock()
        tool_call.id = "test-id"
        tool_call.arguments = {"query": "test", "date_restrict": None}

        result = await tool.run(tool_call)

        assert hasattr(result, "id")
        assert result.id == "test-id"
        assert hasattr(result, "name")
        assert result.name == "WebSearch"
        assert hasattr(result, "content_chunks")
        assert result.content_chunks == sample_content_chunks
        assert (
            not hasattr(result, "error_message")
            or result.error_message is None
            or result.error_message == ""
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__returns_error_response__when_executor_raises_exception(
        self,
        mock_web_search_config_v1: Mock,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify run returns error ToolCallResponse when executor raises exception.
        Why this matters: Ensures error handling works correctly and tool fails gracefully.
        Setup summary: Mock WebSearchTool and executor that raises exception.
        """
        mock_executor = AsyncMock()
        mock_executor.run = AsyncMock(side_effect=Exception("Test error"))
        mock_executor.notify_name = "test-name"
        mock_executor.notify_message = "test-message"

        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")

        # Mock WebSearchDebugInfo to return a proper dict from model_dump
        mock_debug_info_class = Mock()
        mock_debug_info_instance = Mock()
        mock_debug_info_instance.model_dump.return_value = {"test": "debug_info"}
        mock_debug_info_instance.num_chunks_in_final_prompts = None
        mock_debug_info_instance.execution_time = None
        mock_debug_info_class.return_value = mock_debug_info_instance
        mocker.patch(
            "unique_web_search.service.WebSearchDebugInfo", mock_debug_info_class
        )
        
        # Mock WebSearchMessageLogger
        mock_message_logger = Mock()
        mock_message_logger.failed = AsyncMock()
        mocker.patch(
            "unique_web_search.service.WebSearchMessageLogger",
            return_value=mock_message_logger,
        )

        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )
        mocker.patch.object(WebSearchTool, "_get_executor", return_value=mock_executor)

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1
        tool.tool_parameter_calls = WebSearchToolParameters
        tool.logger = Mock()
        tool._message_step_logger = Mock()
        tool._tool_progress_reporter = None
        tool._display_name = "WebSearch"
        tool.company_id = "test-company"
        tool.debug = False
        tool.name = "WebSearch"
        tool.settings = Mock()
        tool.settings.display_name = "WebSearch"

        tool_call = Mock()
        tool_call.id = "test-id"
        tool_call.arguments = {"query": "test", "date_restrict": None}

        result = await tool.run(tool_call)

        assert hasattr(result, "id")
        assert result.id == "test-id"
        assert hasattr(result, "name")
        assert result.name == "WebSearch"
        assert hasattr(result, "error_message")
        assert result.error_message == "Test error"
        assert (
            not hasattr(result, "content_chunks")
            or result.content_chunks is None
            or len(result.content_chunks) == 0
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run__notifies_progress_reporter__when_progress_reporter_exists(
        self,
        mock_web_search_config_v1: Mock,
        mock_tool_progress_reporter: Mock,
        sample_web_search_tool_parameters: WebSearchToolParameters,
        sample_content_chunks: list,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify run notifies progress reporter when it exists.
        Why this matters: Ensures progress reporting works for monitoring tool execution.
        Setup summary: Mock WebSearchTool with progress reporter and successful executor.
        """
        mock_executor = AsyncMock()
        mock_executor.run = AsyncMock(
            return_value=sample_content_chunks
        )
        mock_executor.notify_name = "test-name"
        mock_executor.notify_message = "test-message"

        mocker.patch("unique_web_search.service.get_search_engine_service")
        mocker.patch("unique_web_search.service.get_crawler_service")
        mocker.patch("unique_web_search.service.ChunkRelevancySorter")
        mocker.patch("unique_web_search.service.ContentProcessor")

        # Mock WebSearchDebugInfo to return a proper dict from model_dump
        mock_debug_info_class = Mock()
        mock_debug_info_instance = Mock()
        mock_debug_info_instance.model_dump.return_value = {"test": "debug_info"}
        mock_debug_info_instance.num_chunks_in_final_prompts = None
        mock_debug_info_instance.execution_time = None
        mock_debug_info_class.return_value = mock_debug_info_instance
        mocker.patch(
            "unique_web_search.service.WebSearchDebugInfo", mock_debug_info_class
        )
        
        # Mock WebSearchMessageLogger
        mock_message_logger = Mock()
        mock_message_logger.finished = AsyncMock()
        mocker.patch(
            "unique_web_search.service.WebSearchMessageLogger",
            return_value=mock_message_logger,
        )

        mocker.patch.object(
            WebSearchTool, "__init__", lambda self, config, *args, **kwargs: None
        )
        mocker.patch.object(WebSearchTool, "_get_executor", return_value=mock_executor)

        tool = WebSearchTool.__new__(WebSearchTool)
        tool.config = mock_web_search_config_v1
        tool.tool_parameter_calls = WebSearchToolParameters
        tool.logger = Mock()
        tool._message_step_logger = Mock()
        tool._tool_progress_reporter = mock_tool_progress_reporter
        tool._display_name = "WebSearch"
        tool.company_id = "test-company"
        tool.debug = False
        tool.name = "WebSearch"
        tool.settings = Mock()
        tool.settings.display_name = "WebSearch"

        # Mock feature_flags to ensure the progress reporter code path is taken
        mock_feature_flags = mocker.patch("unique_web_search.service.feature_flags")
        mock_feature_flags.enable_new_answers_ui_un_14411.is_enabled.return_value = False

        tool_call = Mock()
        tool_call.id = "test-id"
        tool_call.arguments = {"query": "test", "date_restrict": None}

        await tool.run(tool_call)

        assert mock_tool_progress_reporter.notify_from_tool_call.called
        call_args = mock_tool_progress_reporter.notify_from_tool_call.call_args
        # The call_args are (args, kwargs), and arguments are passed as positional
        args, kwargs = call_args
        assert len(args) == 4  # tool_call, name, message, state
        assert args[1] == "test-name"  # name argument
        assert args[2] == "test-message"  # message argument
