"""Integration tests for message assessment operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestMessageAssessment:
    """Test message assessment operations."""

    def test_message_assessment_create__creates_assessment__successfully(
        self, request_context, integration_env, cleanup_items
    ):
        """
        Purpose: Verify message assessment creation works.
        Why: Assessment creation is important for message evaluation.
        Setup: Request context and test message ID.
        """
        # Arrange
        test_message_id = integration_env.get("test_message_id")
        if not test_message_id:
            pytest.skip("TEST_MESSAGE_ID required for assessment tests")

        assessment_id = None

        try:
            # Act: Create assessment
            response = unique_SDK.message_assessment.Create.request(
                context=request_context,
                message_id=test_message_id,
                type="quality",
                label="good",
                status="completed",
                explanation="Integration test assessment",
            )

            # Assert
            assert response is not None
            assessment_id = (
                response.id if hasattr(response, "id") else response.get("id")
            )

            if assessment_id:
                cleanup_items.append(("assessment", assessment_id))

                # Act: Update assessment
                update_response = (
                    unique_SDK.message_assessment.messageId.Update.request(
                        context=request_context,
                        message_id=assessment_id,
                        label="excellent",
                    )
                )

                # Assert: Update succeeded
                assert update_response is not None

        finally:
            # Cleanup (if delete endpoint exists)
            pass
