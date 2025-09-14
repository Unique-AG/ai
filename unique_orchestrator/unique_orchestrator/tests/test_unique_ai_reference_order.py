from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_history_updated_before_reference_extraction(monkeypatch):
    # Lazy import to avoid heavy dependencies at module import time
    from unique_orchestrator.unique_ai import UniqueAI

    # Create a minimal UniqueAI instance with mocked dependencies
    mock_logger = MagicMock()

    class DummyEvent:
        class Payload:
            class AssistantMessage:
                id = "assist_1"

            assistant_message = AssistantMessage()
            user_message = MagicMock()
            user_message.text = "query"

        payload = Payload()

    dummy_event = MagicMock()
    dummy_event.payload = DummyEvent.Payload()

    mock_config = MagicMock()
    mock_config.agent.max_loop_iterations = 1
    mock_config.space.language_model.name = "dummy-model"
    mock_config.agent.experimental.temperature = 0.0
    mock_config.agent.experimental.additional_llm_options = {}

    # Managers
    mock_history_manager = MagicMock()
    mock_history_manager.has_no_loop_messages.return_value = True
    mock_history_manager._append_tool_calls_to_history = MagicMock()
    mock_history_manager.add_tool_call_results = MagicMock()

    mock_reference_manager = MagicMock()
    mock_reference_manager.extract_referenceable_chunks = MagicMock()
    mock_reference_manager.get_chunks.return_value = []

    mock_thinking_manager = MagicMock()
    mock_debug_info_manager = MagicMock()
    mock_debug_info_manager.get.return_value = {}
    mock_debug_info_manager.extract_tool_debug_info = MagicMock()

    mock_tool_manager = MagicMock()
    mock_tool_manager.get_forced_tools.return_value = []
    mock_tool_manager.get_tool_definitions.return_value = []
    mock_tool_manager.execute_selected_tools = AsyncMock(return_value=[MagicMock()])
    mock_tool_manager.does_a_tool_take_control.return_value = False

    class DummyStreamResponse:
        def __init__(self):
            self.tool_calls = [MagicMock()]
            self.message = MagicMock()
            self.message.references = []
            self.message.text = ""

        def is_empty(self):
            return False

    mock_chat_service = MagicMock()
    mock_chat_service.complete_with_references_async = AsyncMock(
        return_value=DummyStreamResponse()
    )
    mock_chat_service.modify_assistant_message_async = AsyncMock(return_value=None)
    mock_chat_service.create_assistant_message_async = AsyncMock(
        return_value=MagicMock(id="assist_new")
    )
    mock_content_service = MagicMock()
    mock_history_manager.get_history_for_model_call = AsyncMock(
        return_value=MagicMock()
    )

    # Instantiate
    ua = UniqueAI(
        logger=mock_logger,
        event=dummy_event,
        config=mock_config,
        chat_service=mock_chat_service,
        content_service=mock_content_service,
        debug_info_manager=mock_debug_info_manager,
        reference_manager=mock_reference_manager,
        thinking_manager=mock_thinking_manager,
        tool_manager=mock_tool_manager,
        history_manager=mock_history_manager,
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        mcp_servers=[],
    )

    # Bypass Jinja template compilation by stubbing prompt renderers
    ua._render_user_prompt = AsyncMock(return_value="user")  # type: ignore
    ua._render_system_prompt = AsyncMock(return_value="system")  # type: ignore
    # Avoid creating new assistant messages path
    ua._thinking_manager.thinking_is_displayed = MagicMock(return_value=True)  # type: ignore

    # Spy on call order by recording sequence
    call_sequence = []

    def record_history_add(results):
        call_sequence.append("history_add")

    def record_reference_extract(results):
        call_sequence.append("reference_extract")

    def record_debug_extract(results):
        call_sequence.append("debug_extract")

    mock_history_manager.add_tool_call_results.side_effect = record_history_add
    mock_reference_manager.extract_referenceable_chunks.side_effect = (
        record_reference_extract
    )
    mock_debug_info_manager.extract_tool_debug_info.side_effect = record_debug_extract

    # Run a single iteration
    await ua.run()

    # Verify order: history first, then references, then debug
    assert call_sequence[:3] == [
        "history_add",
        "reference_extract",
        "debug_extract",
    ]
