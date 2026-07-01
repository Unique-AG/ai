"""Tests for the SwotAnalysisTool service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.language_model import LanguageModelFunction

from unique_swot.service import SwotAnalysisTool


def test_complete_deferred_init_sets_up_services_from_event():
    """Test that _complete_deferred_init derives dependent services from the event.

    This covers the deferred-init path used both by the legacy event-based
    constructor and by _on_services_injected() once services are injected.
    """
    tool = object.__new__(SwotAnalysisTool)
    tool._deferred_init_done = False

    event = Mock()
    event.payload.metadata_filter = {"foo": "bar"}
    event.company_id = "company-1"
    event.user_id = "user-1"
    event.payload.chat_id = "chat-1"
    tool._event = event

    with (
        patch("unique_swot.service.KnowledgeBaseService.from_event") as from_event,
        patch("unique_swot.service.ShortTermMemoryService") as short_term_memory,
    ):
        tool._complete_deferred_init()

    from_event.assert_called_once_with(event)
    short_term_memory.assert_called_once_with(
        company_id="company-1",
        user_id="user-1",
        chat_id="chat-1",
        message_id=None,
    )
    assert tool._metadata_filter == {"foo": "bar"}
    assert tool._knowledge_base_service is from_event.return_value
    assert tool._short_term_memory_service is short_term_memory.return_value
    assert tool._deferred_init_done is True


def test_complete_deferred_init_is_idempotent():
    """Test that calling _complete_deferred_init twice only sets up services once."""
    tool = object.__new__(SwotAnalysisTool)
    tool._deferred_init_done = True
    tool._event = Mock()

    with patch("unique_swot.service.KnowledgeBaseService.from_event") as from_event:
        tool._complete_deferred_init()

    from_event.assert_not_called()


def test_complete_deferred_init_noop_without_event():
    """Test that _complete_deferred_init is a no-op when no event is present yet.

    This is the state right after Tool(config) is constructed with only
    services injected but before the event becomes available.
    """
    tool = object.__new__(SwotAnalysisTool)
    tool._deferred_init_done = False

    tool._complete_deferred_init()

    assert tool._deferred_init_done is False


def test_init_completes_deferred_init_eagerly_when_event_already_present():
    """Test that __init__ runs deferred init immediately for the legacy event path.

    Tool.__init__ sets self._event synchronously when constructed with
    Tool(config, event=...), so SwotAnalysisTool must complete its deferred
    setup right away instead of waiting for _on_services_injected().
    """
    event = Mock()
    event.payload.metadata_filter = {"foo": "bar"}
    event.company_id = "company-1"
    event.user_id = "user-1"
    event.payload.chat_id = "chat-1"

    def fake_tool_init(self, configuration, *args, **kwargs) -> None:
        self._event = event

    with (
        patch("unique_swot.service.Tool.__init__", fake_tool_init),
        patch("unique_swot.service.KnowledgeBaseService.from_event") as from_event,
        patch("unique_swot.service.ShortTermMemoryService") as short_term_memory,
    ):
        tool = SwotAnalysisTool(Mock())

    from_event.assert_called_once_with(event)
    short_term_memory.assert_called_once()
    assert tool._deferred_init_done is True


def test_init_defers_init_when_no_event_present():
    """Test that __init__ leaves deferred init pending for the service-injection path.

    Tool.__init__ does not set self._event when constructed with injected
    services only, so setup must wait for _on_services_injected().
    """

    def fake_tool_init(self, configuration, *args, **kwargs) -> None:
        pass

    with patch("unique_swot.service.Tool.__init__", fake_tool_init):
        tool = SwotAnalysisTool(Mock())

    assert tool._deferred_init_done is False


def test_on_services_injected_completes_deferred_init():
    """Test that _on_services_injected() triggers _complete_deferred_init()."""
    tool = object.__new__(SwotAnalysisTool)
    tool._deferred_init_done = False
    tool._complete_deferred_init = Mock()

    tool._on_services_injected()

    tool._complete_deferred_init.assert_called_once()


def test_get_evaluation_checks_returns_empty_list():
    """Test that get_evaluation_checks_based_on_tool_response returns an empty list.

    This method is part of the Tool interface and indicates what evaluation
    metrics should be run based on a tool response. For SWOT Analysis, we
    don't require any specific evaluation checks, so it returns an empty list.
    """
    # Import the class to ensure coverage tracking
    from unique_swot.service import SwotAnalysisTool

    # Create an instance without full initialization using object.__new__
    # This avoids the complex initialization that requires event data
    tool = object.__new__(SwotAnalysisTool)

    # Create a mock tool response
    tool_response = Mock(spec=ToolCallResponse)
    tool_response.id = "test-id"
    tool_response.name = "SwotAnalysis"
    tool_response.content = "Test content"
    tool_response.content_chunks = []

    # Call the method - it doesn't use self attributes, just returns []
    result = tool.get_evaluation_checks_based_on_tool_response(tool_response)

    # Verify it returns an empty list
    assert result == []
    assert isinstance(result, list)
    assert len(result) == 0


def test_evaluation_check_list_returns_empty_list():
    """Test that evaluation_check_list returns an empty list.

    This method indicates the full list of evaluation metrics that this tool
    supports. For SWOT Analysis, no specific evaluation metrics are needed.
    """
    # Create an instance without full initialization
    tool = object.__new__(SwotAnalysisTool)

    # Call the method
    result = tool.evaluation_check_list()

    # Verify it returns an empty list
    assert result == []
    assert isinstance(result, list)


def test_takes_control_returns_true():
    """Test that takes_control returns True.

    The SWOT Analysis tool takes control of the conversation and doesn't
    want the orchestrator to intervene during execution.
    """
    # Create an instance without full initialization
    tool = object.__new__(SwotAnalysisTool)

    # Call the method
    result = tool.takes_control()

    # Verify it returns True
    assert result is True
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_run_calls_set_completed_at_in_finally_on_exception():
    """Test that the finally block calls set_completed_at=True even when an exception occurs.

    This ensures that the chat message is always marked as completed, regardless of
    whether the SWOT analysis succeeds or fails.
    """
    # Create a tool instance
    tool = object.__new__(SwotAnalysisTool)

    # Mock the required attributes
    tool._chat_service = AsyncMock()
    tool._try_load_session_config = Mock()

    # Create a mock session config that will pass the initial check
    mock_session_config = Mock()
    mock_session_config.swot_analysis.company_listing.name = "Test Company"
    mock_session_config.swot_analysis.render_session_info = Mock(
        return_value="Test Info"
    )
    tool._try_load_session_config.return_value = mock_session_config

    # Mock _get_progress_notifier to return a mock that raises an exception
    mock_progress_notifier = AsyncMock()
    mock_progress_notifier.start = AsyncMock(side_effect=Exception("Test error"))
    mock_progress_notifier.finish = AsyncMock()
    tool._get_progress_notifier = Mock(return_value=mock_progress_notifier)

    # Create a mock tool call
    tool_call = Mock(spec=LanguageModelFunction)
    tool_call.id = "test-call-id"
    tool_call.arguments = {"operation": "generate"}

    # Run the method - it should catch the exception
    result = await tool.run(tool_call)

    # Verify the finally block was executed
    # The finally block should call modify_assistant_message_async with set_completed_at=True
    assert tool._chat_service.modify_assistant_message_async.call_count >= 1

    # Find the call with set_completed_at=True (from the finally block)
    calls = tool._chat_service.modify_assistant_message_async.call_args_list
    finally_call_found = False
    for call in calls:
        if call.kwargs.get("set_completed_at") is True and "content" not in call.kwargs:
            finally_call_found = True
            break

    assert finally_call_found, (
        "Finally block should call modify_assistant_message_async with set_completed_at=True"
    )

    # Verify the exception was handled and a ToolCallResponse was returned
    assert isinstance(result, ToolCallResponse)
    assert "Error running SWOT plan" in result.content


@pytest.mark.asyncio
async def test_run_returns_early_when_no_session_config():
    """Test that run returns early when session config is invalid.

    This tests the early return path where the finally block should NOT be executed
    because the try block is never entered.
    """
    # Create a tool instance
    tool = object.__new__(SwotAnalysisTool)

    # Mock the required attributes
    tool._chat_service = AsyncMock()
    tool._try_load_session_config = Mock(return_value=None)  # No session config
    tool.name = "SwotAnalysis"

    # Create a mock tool call
    tool_call = Mock(spec=LanguageModelFunction)
    tool_call.id = "test-call-id"

    # Run the method
    result = await tool.run(tool_call)

    # Verify it returned early with an error
    assert isinstance(result, ToolCallResponse)
    assert "not provided a valid configuration" in result.content

    # Verify modify_assistant_message_async was called with set_completed_at=True
    # (but this is in the early return, not the finally block)
    tool._chat_service.modify_assistant_message_async.assert_called_once()
    assert (
        tool._chat_service.modify_assistant_message_async.call_args.kwargs[
            "set_completed_at"
        ]
        is True
    )
