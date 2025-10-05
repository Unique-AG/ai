"""Integration tests for message log operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestMessageLog:
    """Test message log operations."""

    def test_message_log_create_and_update__logs_execution__successfully(
        self, request_context, integration_env, cleanup_items
    ):
        """
        Purpose: Verify message log create and update operations work.
        Why: Message logging is critical for debugging and monitoring.
        Setup: Request context and test message ID.
        """
        # Arrange
        test_message_id = integration_env.get("test_message_id")
        if not test_message_id:
            pytest.skip("TEST_MESSAGE_ID required")

        log_id = None

        try:
            # Act: Create log entry
            response = unique_SDK.message_log.Create.request(
                context=request_context,
                message_id=test_message_id,
                event_type="execution_start",
                payload={"test": "integration"},
            )

            # Assert
            assert response is not None
            log_id = response.id if hasattr(response, "id") else response.get("id")

            if log_id:
                cleanup_items.append(("message_log", log_id))

                # Act: Update log entry
                update_response = unique_SDK.message_log.messageLogId.Update.request(
                    context=request_context,
                    message_log_id=log_id,
                    status="completed",
                )

                # Assert: Update succeeded
                assert update_response is not None

        finally:
            # Cleanup (if delete endpoint exists)
            pass
