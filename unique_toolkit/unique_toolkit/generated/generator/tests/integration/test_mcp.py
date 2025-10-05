"""Integration tests for MCP (Model Context Protocol) operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestMCPOperations:
    """Test MCP tool calling operations."""

    def test_mcp_call_tool__invokes_tool__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify MCP tool calling works with generated SDK.
        Why: MCP enables extensible tool integration.
        Setup: Request context and test tool configuration.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required for MCP tests")

        # Act
        response = unique_SDK.mcp.call_tool.CallTool.request(
            context=request_context,
            chat_id=test_chat_id,
            tool_name="test_tool",
            parameters={"param1": "value1"},
        )

        # Assert
        assert response is not None
