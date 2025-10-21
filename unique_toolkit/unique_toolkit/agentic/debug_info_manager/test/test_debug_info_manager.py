"""
Test suite for DebugInfoManager class.

This test suite validates the DebugInfoManager's ability to:
1. Initialize with empty debug info
2. Extract tool debug info from ToolCallResponse objects
3. Handle loop iteration indices
4. Add arbitrary key-value pairs to debug info
5. Retrieve the complete debug info dictionary
"""

from unique_toolkit.agentic.debug_info_manager.debug_info_manager import (
    DebugInfoManager,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse


class TestDebugInfoManager:
    """Test suite for DebugInfoManager functionality."""

    def test_init__initializes_empty_debug_info__on_creation(self):
        """Test that DebugInfoManager initializes with empty tools list."""
        manager = DebugInfoManager()

        assert manager.debug_info == {"tools": []}
        assert manager.get() == {"tools": []}

    def test_extract_tool_debug_info__adds_single_tool__with_valid_response(self):
        """Test extracting debug info from a single ToolCallResponse."""
        manager = DebugInfoManager()
        tool_call_response = ToolCallResponse(
            id="tool_1",
            name="TestTool",
            debug_info={"execution_time": "100ms", "status": "success"},
        )

        manager.extract_tool_debug_info([tool_call_response])

        debug_info = manager.get()
        assert len(debug_info["tools"]) == 1
        assert debug_info["tools"][0]["name"] == "TestTool"
        assert debug_info["tools"][0]["info"]["execution_time"] == "100ms"
        assert debug_info["tools"][0]["info"]["status"] == "success"

    def test_extract_tool_debug_info__adds_multiple_tools__with_multiple_responses(
        self,
    ):
        """Test extracting debug info from multiple ToolCallResponse objects."""
        manager = DebugInfoManager()
        tool_call_responses = [
            ToolCallResponse(
                id="tool_1",
                name="SearchTool",
                debug_info={"query": "test query", "results": 5},
            ),
            ToolCallResponse(
                id="tool_2",
                name="CalculatorTool",
                debug_info={"operation": "add", "result": 42},
            ),
            ToolCallResponse(
                id="tool_3",
                name="WeatherTool",
                debug_info={"location": "New York", "temperature": "72F"},
            ),
        ]

        manager.extract_tool_debug_info(tool_call_responses)

        debug_info = manager.get()
        assert len(debug_info["tools"]) == 3
        assert debug_info["tools"][0]["name"] == "SearchTool"
        assert debug_info["tools"][1]["name"] == "CalculatorTool"
        assert debug_info["tools"][2]["name"] == "WeatherTool"

    def test_extract_tool_debug_info__preserves_order__with_sequential_calls(self):
        """Test that multiple calls to extract_tool_debug_info preserve order."""
        manager = DebugInfoManager()

        # First call
        manager.extract_tool_debug_info(
            [ToolCallResponse(id="tool_1", name="Tool1", debug_info={"step": 1})]
        )

        # Second call
        manager.extract_tool_debug_info(
            [ToolCallResponse(id="tool_2", name="Tool2", debug_info={"step": 2})]
        )

        # Third call
        manager.extract_tool_debug_info(
            [ToolCallResponse(id="tool_3", name="Tool3", debug_info={"step": 3})]
        )

        debug_info = manager.get()
        assert len(debug_info["tools"]) == 3
        assert debug_info["tools"][0]["info"]["step"] == 1
        assert debug_info["tools"][1]["info"]["step"] == 2
        assert debug_info["tools"][2]["info"]["step"] == 3

    def test_extract_tool_debug_info__adds_loop_iteration__when_index_provided(self):
        """Test that loop_iteration_index is added to debug info when provided."""
        manager = DebugInfoManager()
        tool_call_response = ToolCallResponse(
            id="tool_1", name="IterativeTool", debug_info={"status": "processing"}
        )

        manager.extract_tool_debug_info([tool_call_response], loop_iteration_index=3)

        debug_info = manager.get()
        assert debug_info["tools"][0]["info"]["loop_iteration"] == 3
        assert debug_info["tools"][0]["info"]["status"] == "processing"

    def test_extract_tool_debug_info__omits_loop_iteration__when_index_is_none(self):
        """Test that loop_iteration is not added when index is None."""
        manager = DebugInfoManager()
        tool_call_response = ToolCallResponse(
            id="tool_1", name="SingleRunTool", debug_info={"status": "complete"}
        )

        manager.extract_tool_debug_info([tool_call_response], loop_iteration_index=None)

        debug_info = manager.get()
        assert "loop_iteration" not in debug_info["tools"][0]["info"]
        assert debug_info["tools"][0]["info"]["status"] == "complete"

    def test_extract_tool_debug_info__handles_empty_debug_info__gracefully(self):
        """Test extracting from ToolCallResponse with empty debug_info dict."""
        manager = DebugInfoManager()
        tool_call_response = ToolCallResponse(
            id="tool_1", name="MinimalTool", debug_info={}
        )

        manager.extract_tool_debug_info([tool_call_response])

        debug_info = manager.get()
        assert len(debug_info["tools"]) == 1
        assert debug_info["tools"][0]["name"] == "MinimalTool"
        assert debug_info["tools"][0]["info"] == {}

    def test_extract_tool_debug_info__handles_empty_list__without_error(self):
        """Test that passing an empty list doesn't cause errors."""
        manager = DebugInfoManager()

        manager.extract_tool_debug_info([])

        debug_info = manager.get()
        assert debug_info["tools"] == []

    def test_add__adds_new_key_value_pair__to_debug_info(self):
        """Test adding a new key-value pair to debug_info."""
        manager = DebugInfoManager()

        manager.add("execution_summary", {"total_time": "500ms", "total_calls": 5})

        debug_info = manager.get()
        assert "execution_summary" in debug_info
        assert debug_info["execution_summary"]["total_time"] == "500ms"
        assert debug_info["execution_summary"]["total_calls"] == 5

    def test_add__preserves_tools_list__when_adding_new_keys(self):
        """Test that add() preserves the tools list."""
        manager = DebugInfoManager()
        manager.extract_tool_debug_info(
            [
                ToolCallResponse(
                    id="tool_1", name="TestTool", debug_info={"test": "data"}
                )
            ]
        )

        manager.add("metadata", {"version": "1.0"})

        debug_info = manager.get()
        assert len(debug_info["tools"]) == 1
        assert debug_info["tools"][0]["name"] == "TestTool"
        assert debug_info["metadata"]["version"] == "1.0"

    def test_add__overwrites_existing_key__when_key_exists(self):
        """Test that add() overwrites an existing key."""
        manager = DebugInfoManager()
        manager.add("status", "in_progress")
        manager.add("status", "completed")

        debug_info = manager.get()
        assert debug_info["status"] == "completed"

    def test_add__adds_multiple_keys__with_sequential_calls(self):
        """Test adding multiple key-value pairs with sequential calls."""
        manager = DebugInfoManager()

        manager.add("key1", "value1")
        manager.add("key2", {"nested": "value2"})
        manager.add("key3", [1, 2, 3])

        debug_info = manager.get()
        assert debug_info["key1"] == "value1"
        assert debug_info["key2"]["nested"] == "value2"
        assert debug_info["key3"] == [1, 2, 3]

    def test_get__returns_complete_debug_info__with_mixed_data(self):
        """Test get() returns complete debug info with tools and custom keys."""
        manager = DebugInfoManager()

        # Add tool debug info
        manager.extract_tool_debug_info(
            [ToolCallResponse(id="tool_1", name="Tool1", debug_info={"data": "test"})],
            loop_iteration_index=0,
        )

        # Add custom keys
        manager.add("start_time", "2025-10-16T10:00:00")
        manager.add("end_time", "2025-10-16T10:01:00")

        debug_info = manager.get()

        assert "tools" in debug_info
        assert "start_time" in debug_info
        assert "end_time" in debug_info
        assert len(debug_info["tools"]) == 1
        assert debug_info["start_time"] == "2025-10-16T10:00:00"

    def test_integration__complete_workflow__with_all_operations(self):
        """Integration test: complete workflow using all DebugInfoManager methods."""
        manager = DebugInfoManager()

        # Initial state
        assert manager.get() == {"tools": []}

        # Add some metadata
        manager.add("session_id", "abc-123")
        manager.add("user_id", "user-456")

        # First tool call (loop iteration 0)
        manager.extract_tool_debug_info(
            [
                ToolCallResponse(
                    id="tool_1",
                    name="SearchTool",
                    debug_info={"query": "AI research", "hits": 100},
                )
            ],
            loop_iteration_index=0,
        )

        # Second tool call (loop iteration 1)
        manager.extract_tool_debug_info(
            [
                ToolCallResponse(
                    id="tool_2",
                    name="AnalysisTool",
                    debug_info={"processed": 50, "relevant": 10},
                ),
                ToolCallResponse(
                    id="tool_3",
                    name="SummaryTool",
                    debug_info={"paragraphs": 3, "words": 250},
                ),
            ],
            loop_iteration_index=1,
        )

        # Add final summary
        manager.add("summary", {"total_tools": 3, "total_iterations": 2})

        # Verify complete debug info
        debug_info = manager.get()

        assert debug_info["session_id"] == "abc-123"
        assert debug_info["user_id"] == "user-456"
        assert len(debug_info["tools"]) == 3
        assert debug_info["tools"][0]["name"] == "SearchTool"
        assert debug_info["tools"][0]["info"]["loop_iteration"] == 0
        assert debug_info["tools"][1]["name"] == "AnalysisTool"
        assert debug_info["tools"][1]["info"]["loop_iteration"] == 1
        assert debug_info["tools"][2]["name"] == "SummaryTool"
        assert debug_info["tools"][2]["info"]["loop_iteration"] == 1
        assert debug_info["summary"]["total_tools"] == 3
