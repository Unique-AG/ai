import pytest

from unique_sdk.api_resources._message_assessment import MessageAssessment


@pytest.mark.integration
class TestMessageAssessment:
    def test_create_message_assessment(self, event):
        """Test creating message assessment synchronously in sandbox."""
        response = MessageAssessment.create(
            user_id=event.user_id,
            company_id=event.company_id,
            messageId=event.assistant_message_id,
            status="PENDING",
            type="HALLUCINATION",
            isVisible=True,
            title="Test Assessment",
            explanation="This is a test assessment",
            label="YELLOW",
        )

        assert response.messageId == event.assistant_message_id
        assert response.status == "PENDING"
        assert response.type == "HALLUCINATION"
        assert response.isVisible is True
        assert response.explanation == "This is a test assessment"
        assert response.label == "YELLOW"

    @pytest.mark.asyncio
    async def test_create_message_assessment_async(self, event):
        """Test creating message assessment asynchronously in sandbox."""
        response = await MessageAssessment.create_async(
            user_id=event.user_id,
            company_id=event.company_id,
            messageId=event.assistant_message_id,
            status="PENDING",
            type="COMPLIANCE",
            isVisible=True,
            title="Test Assessment Async",
            explanation="This is an async test assessment",
            label="RED",
        )

        assert response.messageId == event.assistant_message_id
        assert response.status == "PENDING"
        assert response.type == "COMPLIANCE"
        assert response.isVisible is True
        assert response.explanation == "This is an async test assessment"
        assert response.label == "RED"

    def test_modify_message_assessment(self, event):
        """Test modifying message assessment synchronously in sandbox."""
        response = MessageAssessment.modify(
            user_id=event.user_id,
            company_id=event.company_id,
            messageId=event.assistant_message_id,
            type="COMPLIANCE",
            status="DONE",
            title="Updated Assessment",
            explanation="This is an updated assessment",
            label="GREEN",
        )

        assert response.messageId == event.assistant_message_id
        assert response.status == "DONE"
        assert response.type == "COMPLIANCE"
        assert response.explanation == "This is an updated assessment"
        assert response.label == "GREEN"

    @pytest.mark.asyncio
    async def test_modify_message_assessment_async(self, event):
        """Test modifying message assessment asynchronously in sandbox."""
        response = await MessageAssessment.modify_async(
            user_id=event.user_id,
            company_id=event.company_id,
            messageId=event.assistant_message_id,
            type="HALLUCINATION",
            status="ERROR",
            title="Updated Assessment Async",
            explanation="This is an updated async assessment",
            label="YELLOW",
        )

        assert response.messageId == event.assistant_message_id
        assert response.status == "ERROR"
        assert response.type == "HALLUCINATION"
        assert response.explanation == "This is an updated async assessment"
        assert response.label == "YELLOW"
