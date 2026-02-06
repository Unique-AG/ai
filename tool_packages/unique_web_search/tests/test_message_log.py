"""Tests for WebSearchMessageLogger service.

This module tests the WebSearchMessageLogger class which handles logging
of messages, queries, and search results during web search operations.
"""

from unittest.mock import AsyncMock

import pytest
from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.chat.schemas import (
    MessageLog,
    MessageLogDetails,
    MessageLogStatus,
)
from unique_toolkit.content import ContentReference

from unique_web_search.services.message_log import WebSearchMessageLogger
from unique_web_search.services.search_engine.schema import WebSearchResult


class TestWebSearchMessageLoggerInit:
    """Tests for WebSearchMessageLogger initialization."""

    @pytest.mark.ai
    def test_init__initializes_with_running_status__on_creation(
        self, mock_message_step_logger: MessageStepLogger
    ) -> None:
        """
        Purpose: Verify WebSearchMessageLogger initializes with RUNNING status.
        Why this matters: Initial state must be RUNNING to track ongoing operations.
        Setup summary: Create logger and verify initial status.
        """
        # Arrange & Act
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Assert
        assert logger._status == MessageLogStatus.RUNNING

    @pytest.mark.ai
    def test_init__initializes_empty_details__on_creation(
        self, mock_message_step_logger: MessageStepLogger
    ) -> None:
        """
        Purpose: Verify WebSearchMessageLogger initializes with empty details.
        Why this matters: Details should start empty and be populated during execution.
        Setup summary: Create logger and verify empty details.
        """
        # Arrange & Act
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Assert
        assert isinstance(logger._details, MessageLogDetails)
        assert logger._details.data == []

    @pytest.mark.ai
    def test_init__initializes_empty_references__on_creation(
        self, mock_message_step_logger: MessageStepLogger
    ) -> None:
        """
        Purpose: Verify WebSearchMessageLogger initializes with empty references.
        Why this matters: References should start empty and be added as results come in.
        Setup summary: Create logger and verify empty references list.
        """
        # Arrange & Act
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Assert
        assert isinstance(logger._references, list)
        assert len(logger._references) == 0

    @pytest.mark.ai
    def test_init__initializes_empty_progress_message__on_creation(
        self, mock_message_step_logger: MessageStepLogger
    ) -> None:
        """
        Purpose: Verify WebSearchMessageLogger initializes with empty progress message.
        Why this matters: Progress message should start empty to avoid stale messages.
        Setup summary: Create logger and verify empty progress message.
        """
        # Arrange & Act
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Assert
        assert logger._progress_message == ""

    @pytest.mark.ai
    def test_init__stores_tool_display_name__on_creation(
        self, mock_message_step_logger: MessageStepLogger
    ) -> None:
        """
        Purpose: Verify WebSearchMessageLogger stores the tool display name.
        Why this matters: Display name is used in message log headers.
        Setup summary: Create logger with specific name and verify it's stored.
        """
        # Arrange & Act
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Custom Web Search",
        )

        # Assert
        assert logger._tool_display_name == "Custom Web Search"

    @pytest.mark.ai
    def test_init__initializes_current_message_log_as_none__on_creation(
        self, mock_message_step_logger: MessageStepLogger
    ) -> None:
        """
        Purpose: Verify WebSearchMessageLogger initializes with None message log.
        Why this matters: Message log should be created on first propagation.
        Setup summary: Create logger and verify None current message log.
        """
        # Arrange & Act
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Assert
        assert logger._current_message_log is None


class TestWebSearchMessageLoggerFinished:
    """Tests for WebSearchMessageLogger.finished() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_finished__changes_status_to_completed__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify finished() changes status to COMPLETED.
        Why this matters: Status must reflect completion for UI updates.
        Setup summary: Create logger, call finished(), verify status.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.finished()

        # Assert
        assert logger._status == MessageLogStatus.COMPLETED

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_finished__propagates_message_log__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify finished() propagates the message log.
        Why this matters: Ensures completion status is sent to chat service.
        Setup summary: Mock message step logger, call finished(), verify propagation.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.finished()

        # Assert
        mock_message_step_logger.create_or_update_message_log_async.assert_called_once()
        call_kwargs = (
            mock_message_step_logger.create_or_update_message_log_async.call_args.kwargs
        )
        assert call_kwargs["status"] == MessageLogStatus.COMPLETED

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_finished__includes_tool_display_name_in_header__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify finished() includes tool display name in message log header.
        Why this matters: Header identifies the tool in the UI.
        Setup summary: Create logger with name, call finished(), verify header.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="My Custom Tool",
        )

        # Act
        await logger.finished()

        # Assert
        call_kwargs = (
            mock_message_step_logger.create_or_update_message_log_async.call_args.kwargs
        )
        assert call_kwargs["header"] == "My Custom Tool"


class TestWebSearchMessageLoggerFailed:
    """Tests for WebSearchMessageLogger.failed() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_failed__changes_status_to_failed__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify failed() changes status to FAILED.
        Why this matters: Status must reflect failure for error handling.
        Setup summary: Create logger, call failed(), verify status.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.failed()

        # Assert
        assert logger._status == MessageLogStatus.FAILED

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_failed__propagates_message_log__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify failed() propagates the message log.
        Why this matters: Ensures failure status is sent to chat service.
        Setup summary: Mock message step logger, call failed(), verify propagation.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.failed()

        # Assert
        mock_message_step_logger.create_or_update_message_log_async.assert_called_once()
        call_kwargs = (
            mock_message_step_logger.create_or_update_message_log_async.call_args.kwargs
        )
        assert call_kwargs["status"] == MessageLogStatus.FAILED


class TestWebSearchMessageLoggerLogProgress:
    """Tests for WebSearchMessageLogger.log_progress() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_progress__stores_progress_message__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify log_progress() stores the progress message.
        Why this matters: Progress message must be stored for propagation.
        Setup summary: Create logger, call log_progress(), verify message stored.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_progress("Searching web...")

        # Assert
        assert logger._progress_message == "Searching web..."

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_progress__propagates_message_log__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify log_progress() propagates the message log.
        Why this matters: Progress updates must be sent to chat service immediately.
        Setup summary: Mock message step logger, call log_progress(), verify propagation.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_progress("Processing results...")

        # Assert
        mock_message_step_logger.create_or_update_message_log_async.assert_called_once()
        call_kwargs = (
            mock_message_step_logger.create_or_update_message_log_async.call_args.kwargs
        )
        assert call_kwargs["progress_message"] == "Processing results..."

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_progress__updates_progress_message__on_multiple_calls(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify log_progress() updates progress message on subsequent calls.
        Why this matters: Progress should reflect the latest operation status.
        Setup summary: Create logger, call log_progress() twice, verify last message.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_progress("Step 1")
        await logger.log_progress("Step 2")

        # Assert
        assert logger._progress_message == "Step 2"
        assert (
            mock_message_step_logger.create_or_update_message_log_async.call_count == 2
        )


class TestWebSearchMessageLoggerLogQueries:
    """Tests for WebSearchMessageLogger.log_queries() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_queries__converts_queries_to_events__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify log_queries() converts query strings to MessageLogEvent objects.
        Why this matters: Events are structured format for message log details.
        Setup summary: Create logger, log queries, verify events created.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )
        queries = ["python tutorial", "web scraping guide"]

        # Act
        await logger.log_queries(queries)

        # Assert
        assert len(logger._details.data) == 2
        assert logger._details.data[0].type == "WebSearch"
        assert logger._details.data[0].text == "python tutorial"
        assert logger._details.data[1].type == "WebSearch"
        assert logger._details.data[1].text == "web scraping guide"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_queries__extends_existing_details__when_called_multiple_times(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify log_queries() extends details rather than replacing them.
        Why this matters: Multiple query batches should accumulate in details.
        Setup summary: Create logger, log queries twice, verify cumulative data.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_queries(["query 1"])
        await logger.log_queries(["query 2", "query 3"])

        # Assert
        assert len(logger._details.data) == 3

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_queries__propagates_message_log__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify log_queries() propagates the message log.
        Why this matters: Query logging must be reflected immediately in UI.
        Setup summary: Mock message step logger, log queries, verify propagation.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_queries(["test query"])

        # Assert
        mock_message_step_logger.create_or_update_message_log_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_queries__handles_empty_query_list__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify log_queries() handles empty query lists gracefully.
        Why this matters: Edge case handling prevents errors in query processing.
        Setup summary: Create logger, log empty list, verify no events added.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_queries([])

        # Assert
        assert len(logger._details.data) == 0
        mock_message_step_logger.create_or_update_message_log_async.assert_called_once()


class TestWebSearchMessageLoggerLogWebSearchResults:
    """Tests for WebSearchMessageLogger.log_web_search_results() method."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_web_search_results__converts_results_to_references__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify log_web_search_results() converts results to ContentReference objects.
        Why this matters: References are structured format for content citations.
        Setup summary: Create logger, log results, verify references created.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_web_search_results(sample_web_search_results)

        # Assert
        assert len(logger._references) == 2
        assert isinstance(logger._references[0], ContentReference)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_web_search_results__assigns_sequential_numbers__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify log_web_search_results() assigns sequential sequence numbers.
        Why this matters: Sequence numbers must be unique for citation tracking.
        Setup summary: Create logger, log results, verify sequence numbers.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_web_search_results(sample_web_search_results)

        # Assert
        assert logger._references[0].sequence_number == 0
        assert logger._references[1].sequence_number == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_web_search_results__continues_sequence_numbers__on_multiple_calls(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify log_web_search_results() continues sequence numbers across calls.
        Why this matters: Multiple result batches must have unique sequence numbers.
        Setup summary: Create logger, log results twice, verify continuous numbering.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_web_search_results([sample_web_search_results[0]])
        await logger.log_web_search_results([sample_web_search_results[1]])

        # Assert
        assert len(logger._references) == 2
        assert logger._references[0].sequence_number == 0
        assert logger._references[1].sequence_number == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_web_search_results__propagates_message_log__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify log_web_search_results() propagates the message log.
        Why this matters: Results must be reflected immediately in UI.
        Setup summary: Mock message step logger, log results, verify propagation.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_web_search_results(sample_web_search_results)

        # Assert
        mock_message_step_logger.create_or_update_message_log_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_web_search_results__handles_empty_results_list__when_called(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify log_web_search_results() handles empty results lists gracefully.
        Why this matters: Edge case handling prevents errors when no results found.
        Setup summary: Create logger, log empty list, verify no references added.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Test Tool",
        )

        # Act
        await logger.log_web_search_results([])

        # Assert
        assert len(logger._references) == 0
        mock_message_step_logger.create_or_update_message_log_async.assert_called_once()


class TestWebSearchMessageLoggerIntegration:
    """Integration tests for WebSearchMessageLogger full lifecycle."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_full_lifecycle__tracks_all_operations__from_start_to_finish(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
        sample_web_search_results: list[WebSearchResult],
    ) -> None:
        """
        Purpose: Verify full lifecycle from initialization to completion works correctly.
        Why this matters: Integration test ensures all components work together.
        Setup summary: Create logger, perform operations, finish, verify state.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Web Search Tool",
        )

        # Act
        await logger.log_progress("Starting search...")
        await logger.log_queries(["python tutorial"])
        await logger.log_web_search_results(sample_web_search_results)
        await logger.finished()

        # Assert
        assert logger._status == MessageLogStatus.COMPLETED
        assert len(logger._details.data) == 1
        assert len(logger._references) == 2
        assert logger._progress_message == "Starting search..."
        assert (
            mock_message_step_logger.create_or_update_message_log_async.call_count == 4
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_failure_scenario__tracks_operations_until_failure__when_error_occurs(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify failure scenario properly logs operations until error.
        Why this matters: Failed operations must still capture progress for debugging.
        Setup summary: Create logger, perform operations, fail, verify state.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Web Search Tool",
        )

        # Act
        await logger.log_progress("Starting search...")
        await logger.log_queries(["test query"])
        await logger.failed()

        # Assert
        assert logger._status == MessageLogStatus.FAILED
        assert len(logger._details.data) == 1
        assert logger._progress_message == "Starting search..."
        assert (
            mock_message_step_logger.create_or_update_message_log_async.call_count == 3
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_multiple_query_batches__accumulates_all_queries__across_calls(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify multiple query batches accumulate correctly.
        Why this matters: Complex searches may involve multiple query refinements.
        Setup summary: Create logger, log multiple query batches, verify accumulation.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Web Search Tool",
        )

        # Act
        await logger.log_queries(["query 1", "query 2"])
        await logger.log_queries(["query 3"])
        await logger.log_queries(["query 4", "query 5", "query 6"])

        # Assert
        assert len(logger._details.data) == 6
        assert all(event.type == "WebSearch" for event in logger._details.data)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_multiple_result_batches__maintains_sequence__across_calls(
        self,
        mock_message_step_logger: MessageStepLogger,
        mock_message_log: MessageLog,
    ) -> None:
        """
        Purpose: Verify multiple result batches maintain correct sequence numbers.
        Why this matters: Citations must have unique, continuous sequence numbers.
        Setup summary: Create logger, log multiple result batches, verify sequences.
        """
        # Arrange
        mock_message_step_logger.create_or_update_message_log_async = AsyncMock(
            return_value=mock_message_log
        )
        logger = WebSearchMessageLogger(
            message_step_logger=mock_message_step_logger,
            tool_display_name="Web Search Tool",
        )

        result1 = WebSearchResult(
            url="https://example.com/1",
            title="Result 1",
            snippet="Snippet 1",
            content="Content 1",
        )
        result2 = WebSearchResult(
            url="https://example.com/2",
            title="Result 2",
            snippet="Snippet 2",
            content="Content 2",
        )
        result3 = WebSearchResult(
            url="https://example.com/3",
            title="Result 3",
            snippet="Snippet 3",
            content="Content 3",
        )

        # Act
        await logger.log_web_search_results([result1])
        await logger.log_web_search_results([result2, result3])

        # Assert
        assert len(logger._references) == 3
        assert logger._references[0].sequence_number == 0
        assert logger._references[1].sequence_number == 1
        assert logger._references[2].sequence_number == 2
