"""Integration tests for agent operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestAgentOperations:
    """Test agent execution operations."""

    def test_agent_run__executes_agent__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify agent execution works with generated SDK.
        Why: Agent runs are core AI functionality.
        Setup: Request context and test agent configuration.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        test_assistant_id = integration_env.get("test_assistant_id")

        if not test_chat_id or not test_assistant_id:
            pytest.skip("TEST_CHAT_ID and TEST_ASSISTANT_ID required")

        # Act
        response = unique_SDK.agent.run.RunAgent.request(
            context=request_context,
            chat_id=test_chat_id,
            assistant_id=test_assistant_id,
            input="Integration test input",
            config={},
        )

        # Assert
        assert response is not None
